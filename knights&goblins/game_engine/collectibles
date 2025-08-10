class Collectible:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.collected = False
    
    def collect(self):
        """Обработка сбора предмета"""
        self.collected = True
        return True
    
    def is_collected(self):
        """Проверка, собран ли предмет"""
        return self.collected

class Coin(Collectible):
    def __init__(self, x, y, width=20, height=20, value=10):
        super().__init__(x, y, width, height)
        self.value = value
        self.type = "coin"
    
    def collect(self):
        """Обработка сбора монеты"""
        if not self.collected:
            self.collected = True
            return {"type": "coin", "value": self.value}
        return None

class HealthPotion(Collectible):
    def __init__(self, x, y, width=25, height=25, heal_amount=20):
        super().__init__(x, y, width, height)
        self.heal_amount = heal_amount
        self.type = "health_potion"
    
    def collect(self):
        """Обработка сбора зелья здоровья"""
        if not self.collected:
            self.collected = True
            return {"type": "health_potion", "heal_amount": self.heal_amount}
        return None

class Key(Collectible):
    def __init__(self, x, y, width=25, height=25, door_id=None):
        super().__init__(x, y, width, height)
        self.door_id = door_id
        self.type = "key"
    
    def collect(self):
        """Обработка сбора ключа"""
        if not self.collected:
            self.collected = True
            return {"type": "key", "door_id": self.door_id}
        return None
