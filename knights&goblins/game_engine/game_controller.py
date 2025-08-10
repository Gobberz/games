import time
import json
import os
from .player import Player
from .level import Level
from .physics import Physics
import config

class GameController:
    def __init__(self):
        self.player = None
        self.level = None
        self.physics = Physics(
            gravity=config.PHYSICS["gravity"],
            friction=config.PHYSICS["friction"],
            terminal_velocity=config.PHYSICS["terminal_velocity"]
        )
        self.game_time = 0
        self.last_update_time = time.time()
        self.paused = False
        self.level_completed = False
        self.game_over = False
        self.current_difficulty = "easy"
        self.score = 0
        self.lives = 3
        self.level_number = 1
        self.projectiles = []  # Для хранения всех снарядов в игре
        
        # Попытка загрузить сохраненное состояние
        self.load_game_state()
    
    def initialize_game(self, difficulty="easy", level_number=1):
        """Инициализация новой игры"""
        self.current_difficulty = difficulty
        self.level_number = level_number
        self.score = 0
        self.lives = 3
        self.game_over = False
        self.level_completed = False
        self.game_time = 0
        self.last_update_time = time.time()
        
        # Генерируем уровень
        from ml_system.level_generator import LevelGenerator
        level_generator = LevelGenerator()
        level_data = level_generator.generate_level(difficulty)
        level_data["level_id"] = f"level_{level_number}"
        
        # Создаем уровень и игрока
        self.level = Level(level_data)
        self.player = Player(
            x=self.level.start_x,
            y=self.level.start_y,
            width=config.PLAYER_DEFAULT["width"],
            height=config.PLAYER_DEFAULT["height"],
            speed=config.PLAYER_DEFAULT["speed"],
            jump_strength=config.PLAYER_DEFAULT["jump_strength"],
            health=config.PLAYER_DEFAULT["max_health"]
        )
        
        # Сохраняем начальное состояние
        self.save_game_state()
    
    def load_level(self, level_data):
        """Загрузка уровня из данных"""
        self.level = Level(level_data)
        self.player.x = self.level.start_x
        self.player.y = self.level.start_y
        self.level_completed = False
        self.game_time = 0
        self.last_update_time = time.time()
    
    def reset_level(self):
        """Сброс текущего уровня"""
        if self.level:
            self.player.x = self.level.start_x
            self.player.y = self.level.start_y
            self.player.velocity_x = 0
            self.player.velocity_y = 0
            self.player.health = self.player.max_health
            self.level_completed = False
            self.game_time = 0
            self.last_update_time = time.time()
    
    def update(self):
        """Основной игровой цикл"""
        if self.paused or self.game_over or self.level_completed:
            return
        
        # Вычисляем временной шаг
        current_time = time.time()
        delta_time = current_time - self.last_update_time
        self.last_update_time = current_time
        self.game_time += delta_time
        
        # Обновляем игрока
        self.player.update(delta_time)
        
        # Применяем физику
        self.physics.apply_gravity(self.player)
        self.physics.update_position(self.player, delta_time)
        
        # Обновляем уровень
        self.level.update(delta_time)
        
        # Проверяем столкновения с платформами
        self.player.on_ground = False
        for platform in self.level.platforms:
            if self.physics.check_collision(self.player, platform):
                self.physics.resolve_collision(self.player, platform)
        
        # Проверяем столкновения с врагами
        for enemy in self.level.enemies:
            if enemy.is_alive():
                # Обновляем врага
                enemy.update(delta_time, self.player)
                
                # Проверяем столкновение игрока с врагом
                if self.physics.check_collision(self.player, enemy):
                    if self.player.take_damage(enemy.damage):
                        # Логирование получения урона
                        self.log_action("take_damage")
                
                # Проверяем атаку игрока по врагу
                if self.player.is_attacking:
                    if self.physics.check_entity_hit(self.player, enemy, self.player.attack_range):
                        if enemy.take_damage(self.player.attack_damage):
                            # Логирование убийства врага
                            self.log_action("kill_enemy")
                            self.score += 50
                
                # Проверяем проектили (для лучников)
                if hasattr(enemy, 'projectiles'):
                    for projectile in enemy.projectiles[:]:
                        if self.physics.check_projectile_hit(projectile, self.player):
                            enemy.projectiles.remove(projectile)
                            self.player.take_damage(projectile["damage"])
                            # Логирование получения урона от проектиля
                            self.log_action("hit_by_projectile")
        
        # Проверяем столкновения с ловушками
        for trap in self.level.traps:
            if trap.is_active() and self.physics.check_collision(self.player, trap):
                damage = trap.trigger()
                if damage > 0:
                    self.player.take_damage(damage)
                    # Логирование активации ловушки
                    self.log_action("trap_triggered")
        
        # Проверяем столкновения с коллекционными предметами
        for collectible in self.level.collectibles[:]:
            if not collectible.is_collected() and self.physics.check_collision(self.player, collectible):
                result = collectible.collect()
                if result:
                    if result["type"] == "coin":
                        self.player.collect_coin(result["value"])
                        self.score += result["value"]
                    elif result["type"] == "health_potion":
                        self.player.heal(result["heal_amount"])
                    elif result["type"] == "key":
                        self.player.collect_key(result)
                    
                    # Удаляем собранный предмет из списка
                    self.level.collectibles.remove(collectible)
                    
                    # Логирование сбора предмета
                    self.log_action(f"collect_{result['type']}")
        
        # Проверяем выход за границы уровня
        if self.player.y > config.SCREEN_HEIGHT:
            self.player.take_damage(self.player.health)  # Мгновенная смерть при падении
            self.log_action("fall_death")
            self.lives -= 1
            if self.lives <= 0:
                self.game_over = True
            else:
                self.reset_level()
        
        # Проверяем победу на уровне
        if self.level.check_level_complete(self.player):
            self.level_completed = True
            self.log_action("level_completed")
            self.save_level_stats()
        
        # Проверяем смерть игрока
        if not self.player.is_alive():
            self.lives -= 1
            self.log_action("player_death")
            if self.lives <= 0:
                self.game_over = True
            else:
                self.reset_level()
    
    def log_action(self, action_type):
        """Логирование игровых действий"""
        # Здесь можно добавить логирование действий для ML-анализа
        # например, вызов PlayerAnalyzer.log_action
        pass
    
    def save_game_state(self):
        """Сохранение состояния игры"""
        if not self.player or not self.level:
            return
        
        game_state = {
            "player": {
                "x": self.player.x,
                "y": self.player.y,
                "health": self.player.health,
                "coins": self.player.coins,
                "score": self.player.score,
                "keys": self.player.keys
            },
            "level_number": self.level_number,
            "difficulty": self.current_difficulty,
            "score": self.score,
            "lives": self.lives,
            "game_time": self.game_time
        }
        
        os.makedirs(os.path.dirname(config.PATHS["game_state"]), exist_ok=True)
        with open(config.PATHS["game_state"], 'w') as f:
            json.dump(game_state, f, indent=4)
    
    def load_game_state(self):
        """Загрузка состояния игры"""
        try:
            with open(config.PATHS["game_state"], 'r') as f:
                game_state = json.load(f)
            
            self.level_number = game_state.get("level_number", 1)
            self.current_difficulty = game_state.get("difficulty", "easy")
            self.score = game_state.get("score", 0)
            self.lives = game_state.get("lives", 3)
            self.game_time = game_state.get("game_time", 0)
            
            # Создаем новый уровень с сохраненной сложностью
            from ml_system.level_generator import LevelGenerator
            level_generator = LevelGenerator()
            level_data = level_generator.generate_level(self.current_difficulty)
            level_data["level_id"] = f"level_{self.level_number}"
            self.level = Level(level_data)
            
            # Создаем игрока с сохраненными параметрами
            player_data = game_state.get("player", {})
            self.player = Player(
                x=player_data.get("x", self.level.start_x),
                y=player_data.get("y", self.level.start_y),
                width=config.PLAYER_DEFAULT["width"],
                height=config.PLAYER_DEFAULT["height"],
                speed=config.PLAYER_DEFAULT["speed"],
                jump_strength=config.PLAYER_DEFAULT["jump_strength"],
                health=player_data.get("health", config.PLAYER_DEFAULT["max_health"])
            )
            self.player.coins = player_data.get("coins", 0)
            self.player.score = player_data.get("score", 0)
            self.player.keys = player_data.get("keys", [])
            
            return True
        except (FileNotFoundError, json.JSONDecodeError):
            # Если файл не найден или поврежден, создаем новую игру
            self.initialize_game()
            return False
    
    def save_level_stats(self):
        """Сохранение статистики прохождения уровня"""
        level_stats = {
            "level_id": self.level.level_id,
            "difficulty": self.current_difficulty,
            "completion_time": self.game_time,
            "score": self.score,
            "remaining_health": self.player.health,
            "collected_coins": self.player.coins
        }
        
        try:
            with open(config.PATHS["level_stats"], 'r') as f:
                stats = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            stats = []
        
        stats.append(level_stats)
        
        os.makedirs(os.path.dirname(config.PATHS["level_stats"]), exist_ok=True)
        with open(config.PATHS["level_stats"], 'w') as f:
            json.dump(stats, f, indent=4)
