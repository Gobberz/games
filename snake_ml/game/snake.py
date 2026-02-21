"""
Класс змейки
"""
import pygame
from game.config import *


class Snake:
    def __init__(self):
        """Инициализация змейки"""
        start_x = GRID_WIDTH // 2
        start_y = GRID_HEIGHT // 2
        
        self.body = [(start_x, start_y)]
        for i in range(1, INITIAL_SNAKE_LENGTH):
            self.body.append((start_x - i, start_y))
        
        self.direction = RIGHT
        self.grow_pending = False
    
    def get_head(self):
        """Получить позицию головы"""
        return self.body[0]
    
    def move(self):
        """Переместить змейку"""
        head_x, head_y = self.get_head()
        dir_x, dir_y = self.direction
        
        new_head = (head_x + dir_x, head_y + dir_y)
        
        self.body.insert(0, new_head)
        
        if not self.grow_pending:
            self.body.pop()
        else:
            self.grow_pending = False
    
    def change_direction(self, new_direction):
        """Изменить направление (не позволяет развернуться на 180°)"""
        # Проверяем что новое направление не противоположно текущему
        if (new_direction[0] * -1, new_direction[1] * -1) != self.direction:
            self.direction = new_direction
    
    def grow(self):
        """Увеличить змейку"""
        self.grow_pending = True
    
    def check_collision(self):
        """Проверить столкновение со стенами или собой"""
        head_x, head_y = self.get_head()
        
        # Столкновение со стенами
        if head_x < 0 or head_x >= GRID_WIDTH or head_y < 0 or head_y >= GRID_HEIGHT:
            return True
        
        # Столкновение с собой
        if self.get_head() in self.body[1:]:
            return True
        
        return False
    
    def draw(self, surface):
        """Отрисовать змейку"""
        for i, segment in enumerate(self.body):
            x, y = segment
            rect = pygame.Rect(x * GRID_SIZE, y * GRID_SIZE, GRID_SIZE, GRID_SIZE)
            
            if i == 0:  # Голова
                pygame.draw.rect(surface, DARK_GREEN, rect)
                pygame.draw.rect(surface, GREEN, rect, 2)
            else:  # Тело
                pygame.draw.rect(surface, GREEN, rect)
                pygame.draw.rect(surface, DARK_GREEN, rect, 1)
