class Physics:
    def __init__(self, gravity=0.5, friction=0.8):
        self.gravity = gravity
        self.friction = friction

    def apply_gravity(self, entity):
        entity.velocity_y += self.gravity

    def apply_friction(self, entity):
        entity.velocity_x *= self.friction

    def update_position(self, entity):
        entity.x += entity.velocity_x
        entity.y += entity.velocity_y

    def check_collision(self, entity1, entity2):
        # Простая проверка столкновений (Bounding Box Collision)
        if (entity1.x < entity2.x + entity2.width and
            entity1.x + entity1.width > entity2.x and
            entity1.y < entity2.y + entity2.height and
            entity1.y + entity1.height > entity2.y):
            return True
        return False


