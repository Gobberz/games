class Trap:
    def __init__(self, x, y, width, height, damage):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.damage = damage
        self.active = True
    
    def trigger(self):
        """Срабатывание ловушки"""
        if self.active:
            return self.damage
        return 0
    
    def deactivate(self):
        """Деактивация ловушки"""
        self.active = False
    
    def is_active(self):
        """Проверка, активна ли ловушка"""
        return self.active

class Spike(Trap):
    def __init__(self, x, y, width, height, damage=15):
        super().__init__(x, y, width, height, damage)
        self.type = "spike"
        self.cooldown = 0
        self.cooldown_time = 2.0  # Время перезарядки в секундах
    
    def update(self, delta_time):
        """Обновление состояния ловушки"""
        if not self.active and self.cooldown > 0:
            self.cooldown -= delta_time
            if self.cooldown <= 0:
                self.active = True
                self.cooldown = 0
    
    def trigger(self):
        """Срабатывание шипов"""
        if self.active:
            self.active = False
            self.cooldown = self.cooldown_time
            return self.damage
        return 0
