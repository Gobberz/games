import math
import config

class Physics:
    def __init__(self, gravity=0.5, friction=0.8, terminal_velocity=15):
        self.gravity = gravity
        self.friction = friction
        self.terminal_velocity = terminal_velocity

    def apply_gravity(self, entity):
        """Применение гравитации к сущности"""
        entity.velocity_y += self.gravity
        # Ограничение максимальной скорости падения
        if entity.velocity_y > self.terminal_velocity:
            entity.velocity_y = self.terminal_velocity

    def apply_friction(self, entity):
        """Применение трения к сущности"""
        if abs(entity.velocity_x) > 0.1:
            entity.velocity_x *= self.friction
        else:
            entity.velocity_x = 0

    def update_position(self, entity, delta_time=1.0):
        """Обновление позиции сущности с учетом временного шага"""
        entity.x += entity.velocity_x * delta_time
        entity.y += entity.velocity_y * delta_time

    def check_collision(self, entity1, entity2):
        """Проверка столкновения двух сущностей (AABB)"""
        if (entity1.x < entity2.x + entity2.width and
            entity1.x + entity1.width > entity2.x and
            entity1.y < entity2.y + entity2.height and
            entity1.y + entity1.height > entity2.y):
            return True
        return False
    
    def get_collision_direction(self, entity1, entity2):
        """Определение направления столкновения (top, bottom, left, right)"""
        if not self.check_collision(entity1, entity2):
            return None
        
        # Вычисляем расстояния пересечения по осям
        dx = min(entity1.x + entity1.width, entity2.x + entity2.width) - max(entity1.x, entity2.x)
        dy = min(entity1.y + entity1.height, entity2.y + entity2.height) - max(entity1.y, entity2.y)
        
        # Определяем направление столкновения по наименьшему пересечению
        if dx < dy:
            if entity1.x < entity2.x:
                return "right"
            else:
                return "left"
        else:
            if entity1.y < entity2.y:
                return "bottom"
            else:
                return "top"
    
    def resolve_collision(self, entity, platform):
        """Разрешение столкновения сущности с платформой"""
        direction = self.get_collision_direction(entity, platform)
        
        if direction == "bottom":
            entity.y = platform.y - entity.height
            entity.velocity_y = 0
            if hasattr(entity, 'on_ground'):
                entity.on_ground = True
        elif direction == "top":
            entity.y = platform.y + platform.height
            entity.velocity_y = 0
        elif direction == "left":
            entity.x = platform.x - entity.width
            entity.velocity_x = 0
        elif direction == "right":
            entity.x = platform.x + platform.width
            entity.velocity_x = 0
    
    def check_entity_hit(self, attacker, target, attack_range):
        """Проверка попадания атаки по цели"""
        # Определяем направление атаки
        direction = 1 if hasattr(attacker, 'facing_right') and attacker.facing_right else -1
        
        # Создаем зону атаки
        attack_x = attacker.x + (attacker.width if direction > 0 else -attack_range)
        attack_y = attacker.y
        attack_width = attack_range
        attack_height = attacker.height
        
        # Проверяем пересечение зоны атаки с целью
        if (attack_x < target.x + target.width and
            attack_x + attack_width > target.x and
            attack_y < target.y + target.height and
            attack_y + attack_height > target.y):
            return True
        return False
    
    def check_projectile_hit(self, projectile, target):
        """Проверка попадания снаряда по цели"""
        if (projectile["x"] < target.x + target.width and
            projectile["x"] + projectile["width"] > target.x and
            projectile["y"] < target.y + target.height and
            projectile["y"] + projectile["height"] > target.y):
            return True
        return False
