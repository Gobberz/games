"""
Основной класс игры со сбором данных для ML
"""
import pygame
import json
from datetime import datetime
from game.config import *
from game.snake import Snake
from game.food import Food


class Game:
    def __init__(self):
        """Инициализация игры"""
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Змейка с ML-анализом")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        
        self.reset_game()
    
    def reset_game(self):
        """Сброс игры в начальное состояние"""
        self.snake = Snake()
        self.food = Food()
        self.food.respawn(self.snake.body)
        self.score = 0
        self.game_over = False
        self.game_data = []  # Данные для ML
        self.frame_count = 0
        self.start_time = pygame.time.get_ticks()
    
    def collect_frame_data(self):
        """Сбор данных каждого кадра для анализа"""
        head_x, head_y = self.snake.get_head()
        food_x, food_y = self.food.position
        
        frame_data = {
            'frame': self.frame_count,
            'time': pygame.time.get_ticks() - self.start_time,
            'snake_head': [head_x, head_y],
            'snake_body': list(self.snake.body),
            'snake_length': len(self.snake.body),
            'food_position': [food_x, food_y],
            'direction': self.snake.direction,
            'score': self.score,
            'distance_to_food': abs(head_x - food_x) + abs(head_y - food_y)  # Manhattan distance
        }
        self.game_data.append(frame_data)
        self.frame_count += 1
    
    def save_session(self):
        """Сохранение сессии игры"""
        session = {
            'date': datetime.now().isoformat(),
            'score': self.score,
            'duration': pygame.time.get_ticks() - self.start_time,
            'frames': self.frame_count,
            'final_length': len(self.snake.body),
            'data': self.game_data
        }
        
        filename = f'data/session_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(filename, 'w') as f:
            json.dump(session, f)
        
        return filename
    
    def handle_events(self):
        """Обработка событий"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            if event.type == pygame.KEYDOWN:
                if self.game_over:
                    if event.key == pygame.K_SPACE:
                        return 'analyze'
                    elif event.key == pygame.K_r:
                        self.reset_game()
                else:
                    if event.key == pygame.K_UP or event.key == pygame.K_w:
                        self.snake.change_direction(UP)
                    elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                        self.snake.change_direction(DOWN)
                    elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
                        self.snake.change_direction(LEFT)
                    elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                        self.snake.change_direction(RIGHT)
        
        return True
    
    def update(self):
        """Обновление состояния игры"""
        if self.game_over:
            return
        
        self.collect_frame_data()
        
        self.snake.move()
        
        # Проверка поедания еды
        if self.snake.get_head() == self.food.position:
            self.snake.grow()
            self.score += 1
            self.food.respawn(self.snake.body)
        
        # Проверка столкновений
        if self.snake.check_collision():
            self.game_over = True
            self.session_file = self.save_session()
    
    def draw(self):
        """Отрисовка игры"""
        self.screen.fill(BLACK)
        
        # Рисуем сетку
        for x in range(0, WINDOW_WIDTH, GRID_SIZE):
            pygame.draw.line(self.screen, (40, 40, 40), (x, 0), (x, WINDOW_HEIGHT))
        for y in range(0, WINDOW_HEIGHT, GRID_SIZE):
            pygame.draw.line(self.screen, (40, 40, 40), (0, y), (WINDOW_WIDTH, y))
        
        # Рисуем еду и змейку
        self.food.draw(self.screen)
        self.snake.draw(self.screen)
        
        # Рисуем счет
        score_text = self.font.render(f'Счет: {self.score}', True, WHITE)
        self.screen.blit(score_text, (10, 10))
        
        # Рисуем длину
        length_text = self.small_font.render(f'Длина: {len(self.snake.body)}', True, WHITE)
        self.screen.blit(length_text, (10, 50))
        
        if self.game_over:
            # Затемнение
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
            overlay.set_alpha(200)
            overlay.fill(BLACK)
            self.screen.blit(overlay, (0, 0))
            
            # Надписи
            game_over_text = self.font.render('ИГРА ОКОНЧЕНА', True, RED)
            score_text = self.font.render(f'Финальный счет: {self.score}', True, WHITE)
            restart_text = self.small_font.render('R - Заново | SPACE - Анализ', True, YELLOW)
            
            self.screen.blit(game_over_text, 
                           (WINDOW_WIDTH // 2 - game_over_text.get_width() // 2, 200))
            self.screen.blit(score_text, 
                           (WINDOW_WIDTH // 2 - score_text.get_width() // 2, 260))
            self.screen.blit(restart_text, 
                           (WINDOW_WIDTH // 2 - restart_text.get_width() // 2, 320))
        
        pygame.display.flip()
    
    def run(self):
        """Главный игровой цикл"""
        running = True
        
        while running:
            result = self.handle_events()
            
            if result == False:
                running = False
            elif result == 'analyze':
                return self.session_file
            
            self.update()
            self.draw()
            self.clock.tick(FPS)
        
        pygame.quit()
        return None
