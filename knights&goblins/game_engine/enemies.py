import math
import random
import config

class Enemy:
    def __init__(self, x, y, width, height, speed, health, damage, enemy_type="goblin"):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.speed = speed
        self.health = health
        self.max_health = health
        self.damage = damage
        self.velocity_x = speed
        self.velocity_y = 0
        self.enemy_type = enemy_type
        self.attack_cooldown = 0
        self.detection_range = config.ENEMY_TYPES[enemy_type]['detection_range']
        self.attack_range = config.ENEMY_TYPES[enemy_type]['attack_range']
        self.state = "patrol"  # patrol, chase, attack

    def update(self, delta_time):
        """Общее обновление состояния врага"""
        if self.attack_cooldown > 0:
            self.attack_cooldown -= delta_time
    
    def move(self):
        """Базовое движение"""
        self.x += self.velocity_x
    
    def take_damage(self, amount):
        """Получение урона"""
        self.health -= amount
        if self.health < 0:
            self.health = 0
        return self.is_alive()
    
    def is_alive(self):
        """Проверка, жив ли враг"""
        return self.health > 0
    
    def reverse_direction(self):
        """Изменение направления движения"""
        self.velocity_x *= -1
    
    def detect_player(self, player):
        """Обнаружение игрока в радиусе видимости"""
        distance = math.sqrt((player.x - self.x)**2 + (player.y - self.y)**2)
        return distance <= self.detection_range
    
    def can_attack(self, player):
        """Проверка, может ли враг атаковать игрока"""
        distance = math.sqrt((player.x - self.x)**2 + (player.y - self.y)**2)
        return distance <= self.attack_range and self.attack_cooldown <= 0
    
    def attack(self, player):
        """Базовая атака"""
        if self.can_attack(player):
            player.take_damage(self.damage)
            self.attack_cooldown = 1.0  # базовое время перезарядки
            return True
        return False

class Goblin(Enemy):
    def __init__(self, x, y, width=50, height=50, speed=2, health=30, damage=10):
        super().__init__(x, y, width, height, speed, health, damage, "goblin")
    
    def update(self, delta_time, player=None):
        """Обновление состояния гоблина"""
        super().update(delta_time)
        
        # Патрулирование если игрок не задан или не обнаружен
        if not player or not self.detect_player(player):
            self.state = "patrol"
            self.move()
        else:
            # Преследование игрока
            self.state = "chase"
            if player.x < self.x:
                self.velocity_x = -self.speed
            else:
                self.velocity_x = self.speed
            
            self.move()
            
            # Атака если возможно
            if self.can_attack(player):
                self.state = "attack"
                self.attack(player)

class Archer(Enemy):
    def __init__(self, x, y, width=50, height=50, speed=1, health=20, damage=15):
        super().__init__(x, y, width, height, speed, health, damage, "archer")
        self.projectiles = []
        self.projectile_speed = config.ENEMY_TYPES["archer"]["projectile_speed"]
    
    def update(self, delta_time, player=None):
        """Обновление состояния лучника"""
        super().update(delta_time)
        
        # Обновление проектилей
        for projectile in self.projectiles[:]:
            projectile["x"] += projectile["velocity_x"] * delta_time * 60
            projectile["y"] += projectile["velocity_y"] * delta_time * 60
            
            # Удаление проектилей, которые вышли за пределы экрана
            if (projectile["x"] < 0 or projectile["x"] > config.SCREEN_WIDTH or
                projectile["y"] < 0 or projectile["y"] > config.SCREEN_HEIGHT):
                self.projectiles.remove(projectile)
        
        if not player or not self.detect_player(player):
            self.state = "patrol"
            self.move()
        else:
            # Лучник не преследует игрока, а старается держать дистанцию
            self.state = "attack"
            
            # Если игрок слишком близко, отходим
            distance = math.sqrt((player.x - self.x)**2 + (player.y - self.y)**2)
            if distance < self.attack_range / 2:
                if player.x < self.x:
                    self.velocity_x = self.speed
                else:
                    self.velocity_x = -self.speed
                self.move()
            else:
                self.velocity_x = 0
            
            # Стреляем если возможно
            if self.can_attack(player):
                self.shoot_at(player)
    
    def shoot_at(self, target):
        """Выстрел в цель"""
        if self.attack_cooldown <= 0:
            # Вычисляем направление к цели
            dx = target.x - self.x
            dy = target.y - self.y
            distance = max(1, math.sqrt(dx*dx + dy*dy))
            
            # Нормализуем вектор направления
            dx /= distance
            dy /= distance
            
            # Создаем проектиль
            projectile = {
                "x": self.x,
                "y": self.y,
                "width": 10,
                "height": 10,
                "velocity_x": dx * self.projectile_speed,
                "velocity_y": dy * self.projectile_speed,
                "damage": self.damage
            }
            
            self.projectiles.append(projectile)
            self.attack_cooldown = 2.0  # Лучник перезаряжается дольше
            return True
        return False

class Troll(Enemy):
    def __init__(self, x, y, width=60, height=60, speed=1, health=60, damage=20):
        super().__init__(x, y, width, height, speed, health, damage, "troll")
        self.charge_cooldown = 0
        self.is_charging = False
        self.charge_speed = speed * 3
    
    def update(self, delta_time, player=None):
        """Обновление состояния тролля"""
        super().update(delta_time)
        
        if self.is_charging:
            # Продолжаем заряд
            self.move()
            self.charge_cooldown -= delta_time
            if self.charge_cooldown <= 0:
                self.is_charging = False
                self.velocity_x = self.speed if self.velocity_x > 0 else -self.speed
        else:
            if not player or not self.detect_player(player):
                self.state = "patrol"
                self.move()
            else:
                # Преследование игрока
                self.state = "chase"
                if player.x < self.x:
                    self.velocity_x = -self.speed
                else:
                    self.velocity_x = self.speed
                
                self.move()
                
                # Атака если возможно
                if self.can_attack(player):
                    self.state = "attack"
                    if random.random() < 0.3:  # 30% шанс на рывок
                        self.charge_at(player)
                    else:
                        self.attack(player)
    
    def charge_at(self, target):
        """Рывок в направлении цели"""
        if not self.is_charging and self.attack_cooldown <= 0:
            self.is_charging = True
            self.charge_cooldown = 1.0
            
            # Направление рывка
            if target.x < self.x:
                self.velocity_x = -self.charge_speed
            else:
                self.velocity_x = self.charge_speed
            
            self.attack_cooldown = 3.0  # Длительное время перезарядки после рывка
            return True
        return False
