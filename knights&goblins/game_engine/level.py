import random
from .platform import Platform, MovingPlatform
from .enemies import Goblin, Archer, Troll
from .collectibles import Coin, HealthPotion, Key
from .traps import Spike
import config

class Level:
    def __init__(self, level_data):
        self.platforms = []
        self.enemies = []
        self.collectibles = []
        self.traps = []
        self.doors = []
        self.start_x = level_data.get('start_x', 50)
        self.start_y = level_data.get('start_y', 400)
        self.end_x = level_data.get('end_x', 750)
        self.end_y = level_data.get('end_y', 400)
        self.level_id = level_data.get('level_id', 'level_1')
        self.difficulty = level_data.get('difficulty', 'easy')
        self.time_limit = level_data.get('time_limit', None)  # в секундах, None = без ограничения
        self.objectives = level_data.get('objectives', {'collect_all': False, 'defeat_all': False})
        
        # Загружаем платформы
        for p_data in level_data.get('platforms', []):
            if p_data.get('moving', False):
                self.platforms.append(MovingPlatform(
                    p_data['x'], p_data['y'], p_data['width'], p_data['height'],
                    p_data.get('move_distance', 100),
                    p_data.get('move_speed', 2),
                    p_data.get('move_direction', 'horizontal')
                ))
            else:
                self.platforms.append(Platform(
                    p_data['x'], p_data['y'], p_data['width'], p_data['height'],
                    p_data.get('destructible', False)
                ))
        
        # Загружаем врагов
        for e_data in level_data.get('enemies', []):
            enemy_type = e_data.get('type', 'goblin')
            if enemy_type == 'goblin':
                self.enemies.append(Goblin(
                    e_data['x'], e_data['y'], 
                    e_data.get('width', config.ENEMY_TYPES['goblin']['width']), 
                    e_data.get('height', config.ENEMY_TYPES['goblin']['height']),
                    e_data.get('speed', config.ENEMY_TYPES['goblin']['speed']),
                    e_data.get('health', config.ENEMY_TYPES['goblin']['health']),
                    e_data.get('damage', config.ENEMY_TYPES['goblin']['damage'])
                ))
            elif enemy_type == 'archer':
                self.enemies.append(Archer(
                    e_data['x'], e_data['y'],
                    e_data.get('width', config.ENEMY_TYPES['archer']['width']),
                    e_data.get('height', config.ENEMY_TYPES['archer']['height']),
                    e_data.get('speed', config.ENEMY_TYPES['archer']['speed']),
                    e_data.get('health', config.ENEMY_TYPES['archer']['health']),
                    e_data.get('damage', config.ENEMY_TYPES['archer']['damage'])
                ))
            elif enemy_type == 'troll':
                self.enemies.append(Troll(
                    e_data['x'], e_data['y'],
                    e_data.get('width', config.ENEMY_TYPES['troll']['width']),
                    e_data.get('height', config.ENEMY_TYPES['troll']['height']),
                    e_data.get('speed', config.ENEMY_TYPES['troll']['speed']),
                    e_data.get('health', config.ENEMY_TYPES['troll']['health']),
                    e_data.get('damage', config.ENEMY_TYPES['troll']['damage'])
                ))
        
        # Загружаем коллекционные предметы
        for c_data in level_data.get('collectibles', []):
            collectible_type = c_data.get('type', 'coin')
            if collectible_type == 'coin':
                self.collectibles.append(Coin(
                    c_data['x'], c_data['y'],
                    c_data.get('width', config.COLLECTIBLE_TYPES['coin']['width']),
                    c_data.get('height', config.COLLECTIBLE_TYPES['coin']['height']),
                    c_data.get('value', config.COLLECTIBLE_TYPES['coin']['value'])
                ))
            elif collectible_type == 'health_potion':
                self.collectibles.append(HealthPotion(
                    c_data['x'], c_data['y'],
                    c_data.get('width', config.COLLECTIBLE_TYPES['health_potion']['width']),
                    c_data.get('height', config.COLLECTIBLE_TYPES['health_potion']['height']),
                    c_data.get('heal_amount', config.COLLECTIBLE_TYPES['health_potion']['heal_amount'])
                ))
            elif collectible_type == 'key':
                self.collectibles.append(Key(
                    c_data['x'], c_data['y'],
                    c_data.get('width', config.COLLECTIBLE_TYPES['key']['width']),
                    c_data.get('height', config.COLLECTIBLE_TYPES['key']['height']),
                    c_data.get('door_id', None)
                ))
        
        # Загружаем ловушки
        for t_data in level_data.get('traps', []):
            trap_type = t_data.get('type', 'spike')
            if trap_type == 'spike':
                self.traps.append(Spike(
                    t_data['x'], t_data['y'], t_data['width'], t_data['height'],
                    t_data.get('damage', 15)
                ))
    
    def update(self, delta_time):
        """Обновление всех элементов уровня"""
        # Обновление движущихся платформ
        for platform in self.platforms:
            if hasattr(platform, 'update'):
                platform.update(delta_time)
        
        # Обновление врагов
        for enemy in self.enemies:
            if enemy.is_alive():
                enemy.update(delta_time)
    
    def get_remaining_enemies(self):
        """Возвращает количество оставшихся врагов"""
        return sum(1 for enemy in self.enemies if enemy.is_alive())
    
    def get_remaining_collectibles(self):
        """Возвращает количество оставшихся коллекционных предметов"""
        return len(self.collectibles)
    
    def check_level_complete(self, player):
        """Проверяет, выполнены ли все цели уровня"""
        if player.x >= self.end_x and player.y >= self.end_y:
            # Проверяем дополнительные цели, если они установлены
            if self.objectives.get('collect_all') and self.get_remaining_collectibles() > 0:
                return False
            if self.objectives.get('defeat_all') and self.get_remaining_enemies() > 0:
                return False
            return True
        return False
