class Goblin:
    def __init__(self, x, y, width, height, speed=2, health=30, damage=10):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.speed = speed
        self.health = health
        self.damage = damage
        self.velocity_x = speed
        self.velocity_y = 0

    def move(self):
        self.x += self.velocity_x

    def take_damage(self, amount):
        self.health -= amount
        if self.health < 0:
            self.health = 0

    def is_alive(self):
        return self.health > 0

    def reverse_direction(self):
        self.velocity_x *= -1


