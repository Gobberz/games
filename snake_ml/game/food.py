"""
Класс еды
"""
import pygame
import random
from game.config import *


class Food:
    def __init__(self):
        """Инициализация еды"""
        self.position = self.generate_position()
    
    def generate_position(self, snake_body=None):
        """Генерация случайной позиции для еды"""
        while True:
            x = random.randint(0, GRID_WIDTH - 1)
            y = random.randint(0, GRID_HEIGHT - 1)
            position = (x, y)
            
            # Убедиться что еда не появилась на змейке
            if snake_body is None or position not in snake_body:
                return position
    
    def respawn(self, snake_body):
        """Переместить еду в новое место"""
        self.position = self.generate_position(snake_body)
    
    def draw(self, surface):
        """Отрисовать еду"""
        x, y = self.position
        rect = pygame.Rect(x * GRID_SIZE, y * GRID_SIZE, GRID_SIZE, GRID_SIZE)
        pygame.draw.rect(surface, RED, rect)
        pygame.draw.rect(surface, (200, 0, 0), rect, 2)
