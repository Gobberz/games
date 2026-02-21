class Platform:
    def __init__(self, x, y, width, height, destructible=False):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.destructible = destructible
        self.durability = 3 if destructible else float('inf')  # Количество ударов до разрушения
    
    def hit(self):
        """Обработка удара по платформе"""
        if self.destructible:
            self.durability -= 1
            return self.durability <= 0
        return False
    
    def is_destructible(self):
        """Проверка, является ли платформа разрушаемой"""
        return self.destructible

class MovingPlatform(Platform):
    def __init__(self, x, y, width, height, move_distance, move_speed=2, move_direction='horizontal'):
        super().__init__(x, y, width, height)
        self.move_distance = move_distance
        self.move_speed = move_speed
        self.move_direction = move_direction  # 'horizontal' или 'vertical'
        self.initial_x = x
        self.initial_y = y
        self.move_timer = 0
        self.direction = 1  # 1 или -1 для направления движения
    
    def update(self, delta_time):
        """Обновление положения движущейся платформы"""
        self.move_timer += delta_time * self.move_speed
        
        if self.move_direction == 'horizontal':
            # Горизонтальное движение по синусоиде
            offset = self.direction * (self.move_distance / 2) * (1 + self.move_timer % 2 - 1)
            
            # Проверка границ движения
            if offset > self.move_distance / 2:
                self.direction = -1
            elif offset < -self.move_distance / 2:
                self.direction = 1
                
            self.x = self.initial_x + offset
        else:
            # Вертикальное движение по синусоиде
            offset = self.direction * (self.move_distance / 2) * (1 + self.move_timer % 2 - 1)
            
            # Проверка границ движения
            if offset > self.move_distance / 2:
                self.direction = -1
            elif offset < -self.move_distance / 2:
                self.direction = 1
                
            self.y = self.initial_y + offset
