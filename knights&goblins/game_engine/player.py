import time
import sys
import os

# Добавляем корневую директорию проекта в sys.path для импорта config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

class Player:
    def __init__(self, x, y, width=50, height=50, speed=5, jump_strength=10, health=100):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.speed = speed
        self.jump_strength = jump_strength
        self.health = health
        self.max_health = health
        self.velocity_x = 0
        self.velocity_y = 0
        self.on_ground = False
        self.facing_right = True
        self.coins = 0
        self.score = 0
        self.keys = []
        self.attack_cooldown = 0
        self.attack_damage = config.PLAYER_DEFAULT["attack_damage"]
        self.attack_range = 60
        self.is_attacking = False
        self.attack_start_time = 0
        self.attack_duration = 0.3  # длительность анимации атаки в секундах
        self.double_jump_available = True
        self.dash_cooldown = 0
        self.dash_duration = 0
        self.dash_speed = 12
        self.invulnerable = False
        self.invulnerable_time = 0
        self.invulnerable_duration = 1.0  # время неуязвимости после получения урона

    def update(self, delta_time):
        """Обновление состояния игрока"""
        # Обработка атаки
        if self.is_attacking:
            if time.time() - self.attack_start_time > self.attack_duration:
                self.is_attacking = False
        
        # Обработка перезарядки атаки
        if self.attack_cooldown > 0:
            self.attack_cooldown -= delta_time
        
        # Обработка рывка
        if self.dash_duration > 0:
            self.dash_duration -= delta_time
            if self.dash_duration <= 0:
                # Завершение рывка
                self.velocity_x = 0
        
        # Обработка перезарядки рывка
        if self.dash_cooldown > 0:
            self.dash_cooldown -= delta_time
        
        # Обработка неуязвимости
        if self.invulnerable:
            self.invulnerable_time -= delta_time
            if self.invulnerable_time <= 0:
                self.invulnerable = False

    def move_left(self):
        """Движение влево"""
        if self.dash_duration <= 0:  # Не позволяем менять направление во время рывка
            self.velocity_x = -self.speed
            self.facing_right = False

    def move_right(self):
        """Движение вправо"""
        if self.dash_duration <= 0:  # Не позволяем менять направление во время рывка
            self.velocity_x = self.speed
            self.facing_right = True

    def stop_move(self):
        """Остановка движения"""
        if self.dash_duration <= 0:  # Не позволяем останавливаться во время рывка
            self.velocity_x = 0

    def jump(self):
        """Прыжок"""
        if self.on_ground:
            self.velocity_y = -self.jump_strength
            self.on_ground = False
            self.double_jump_available = True
            return True
        elif self.double_jump_available:
            # Двойной прыжок
            self.velocity_y = -self.jump_strength * 0.8
            self.double_jump_available = False
            return True
        return False

    def dash(self):
        """Рывок в направлении движения"""
        if self.dash_cooldown <= 0 and self.dash_duration <= 0:
            direction = 1 if self.facing_right else -1
            self.velocity_x = direction * self.dash_speed
            self.dash_duration = 0.2  # длительность рывка в секундах
            self.dash_cooldown = 1.0  # перезарядка рывка в секундах
            self.invulnerable = True
            self.invulnerable_time = self.dash_duration
            return True
        return False

    def attack(self):
        """Атака"""
        if not self.is_attacking and self.attack_cooldown <= 0:
            self.is_attacking = True
            self.attack_start_time = time.time()
            self.attack_cooldown = config.PLAYER_DEFAULT["attack_cooldown"]
            return True
        return False

    def take_damage(self, amount):
        """Получение урона"""
        if not self.invulnerable:
            self.health -= amount
            if self.health < 0:
                self.health = 0
            
            # Становимся неуязвимыми на некоторое время после получения урона
            self.invulnerable = True
            self.invulnerable_time = self.invulnerable_duration
            
            return True
        return False

    def heal(self, amount):
        """Восстановление здоровья"""
        self.health = min(self.health + amount, self.max_health)

    def collect_coin(self, value):
        """Сбор монеты"""
        self.coins += value
        self.score += value

    def collect_key(self, key_data):
        """Сбор ключа"""
        self.keys.append(key_data["door_id"])
        self.score += 50

    def has_key_for_door(self, door_id):
        """Проверка наличия ключа для двери"""
        return door_id in self.keys
    
    def use_key(self, door_id):
        """Использование ключа"""
        if door_id in self.keys:
            self.keys.remove(door_id)
            return True
        return False

    def is_alive(self):
        """Проверка, жив ли игрок"""
        return self.health > 0
