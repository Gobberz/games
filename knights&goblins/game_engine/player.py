class Player:
    def __init__(self, x, y, width, height, speed=5, jump_strength=10, health=100):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.speed = speed
        self.jump_strength = jump_strength
        self.health = health
        self.velocity_x = 0
        self.velocity_y = 0
        self.on_ground = False

    def move_left(self):
        self.velocity_x = -self.speed

    def move_right(self):
        self.velocity_x = self.speed

    def stop_move(self):
        self.velocity_x = 0

    def jump(self):
        if self.on_ground:
            self.velocity_y = -self.jump_strength
            self.on_ground = False

    def take_damage(self, amount):
        self.health -= amount
        if self.health < 0:
            self.health = 0

    def is_alive(self):
        return self.health > 0


