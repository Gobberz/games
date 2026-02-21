"""
Демонстрационный режим AI
"""
import pygame
from game.config import *
from game.snake import Snake
from game.food import Food
from ml.ai_player import SnakeAI


class AIDemo:
    def __init__(self, speed_multiplier=1):
        """Инициализация демо режима"""
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Змейка - AI Демонстрация")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        
        self.speed_multiplier = speed_multiplier
        self.reset_game()
    
    def reset_game(self):
        """Сброс игры"""
        self.snake = Snake()
        self.food = Food()
        self.food.respawn(self.snake.body)
        self.ai = SnakeAI(self.snake, self.food)
        self.score = 0
        self.game_over = False
        self.moves = 0
        self.start_time = pygame.time.get_ticks()
    
    def update(self):
        """Обновление игры"""
        if self.game_over:
            return
        
        # AI делает ход
        direction = self.ai.get_next_move()
        self.snake.change_direction(direction)
        
        self.snake.move()
        self.moves += 1
        
        # Проверка поедания еды
        if self.snake.get_head() == self.food.position:
            self.snake.grow()
            self.score += 1
            self.food.respawn(self.snake.body)
        
        # Проверка столкновений
        if self.snake.check_collision():
            self.game_over = True
    
    def draw(self):
        """Отрисовка"""
        self.screen.fill(BLACK)
        
        # Сетка
        for x in range(0, WINDOW_WIDTH, GRID_SIZE):
            pygame.draw.line(self.screen, (40, 40, 40), (x, 0), (x, WINDOW_HEIGHT))
        for y in range(0, WINDOW_HEIGHT, GRID_SIZE):
            pygame.draw.line(self.screen, (40, 40, 40), (0, y), (WINDOW_WIDTH, y))
        
        # Еда и змейка
        self.food.draw(self.screen)
        self.snake.draw(self.screen)
        
        # Статистика
        score_text = self.font.render(f'AI Счет: {self.score}', True, BLUE)
        self.screen.blit(score_text, (10, 10))
        
        length_text = self.small_font.render(f'Длина: {len(self.snake.body)}', True, WHITE)
        self.screen.blit(length_text, (10, 50))
        
        moves_text = self.small_font.render(f'Ходов: {self.moves}', True, WHITE)
        self.screen.blit(moves_text, (10, 75))
        
        efficiency = (self.score / max(self.moves, 1)) * 100
        eff_text = self.small_font.render(f'Эффективность: {efficiency:.2f}%', True, YELLOW)
        self.screen.blit(eff_text, (10, 100))
        
        # Показываем путь AI
        path = self.ai.find_path_to_food()
        if path:
            for i in range(len(path) - 1):
                start = path[i]
                end = path[i + 1]
                
                start_pixel = (start[0] * GRID_SIZE + GRID_SIZE // 2, 
                             start[1] * GRID_SIZE + GRID_SIZE // 2)
                end_pixel = (end[0] * GRID_SIZE + GRID_SIZE // 2, 
                           end[1] * GRID_SIZE + GRID_SIZE // 2)
                
                pygame.draw.line(self.screen, BLUE, start_pixel, end_pixel, 2)
        
        if self.game_over:
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
            overlay.set_alpha(200)
            overlay.fill(BLACK)
            self.screen.blit(overlay, (0, 0))
            
            game_over_text = self.font.render('AI ПРОИГРАЛ', True, RED)
            score_text = self.font.render(f'Финальный счет: {self.score}', True, WHITE)
            restart_text = self.small_font.render('SPACE - Перезапустить | Q - Выход', True, YELLOW)
            
            self.screen.blit(game_over_text, 
                           (WINDOW_WIDTH // 2 - game_over_text.get_width() // 2, 200))
            self.screen.blit(score_text, 
                           (WINDOW_WIDTH // 2 - score_text.get_width() // 2, 260))
            self.screen.blit(restart_text, 
                           (WINDOW_WIDTH // 2 - restart_text.get_width() // 2, 320))
        
        pygame.display.flip()
    
    def handle_events(self):
        """Обработка событий"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
                    return False
                elif event.key == pygame.K_SPACE and self.game_over:
                    self.reset_game()
                elif event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
                    self.speed_multiplier = min(5, self.speed_multiplier + 0.5)
                elif event.key == pygame.K_MINUS:
                    self.speed_multiplier = max(0.5, self.speed_multiplier - 0.5)
        
        return True
    
    def run(self):
        """Главный цикл"""
        running = True
        
        while running:
            if not self.handle_events():
                running = False
            
            self.update()
            self.draw()
            self.clock.tick(FPS * self.speed_multiplier)
        
        pygame.quit()
