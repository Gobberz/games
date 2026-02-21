"""
Визуализатор результатов анализа
"""
import pygame
import json
from game.config import *


class AnalysisViewer:
    def __init__(self, session_file, report):
        """Инициализация визуализатора"""
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Анализ игры - Змейка")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 28)
        self.small_font = pygame.font.Font(None, 20)
        self.title_font = pygame.font.Font(None, 36)
        
        with open(session_file, 'r') as f:
            self.session = json.load(f)
        
        self.report = report
        self.current_page = 0
        self.max_pages = 2
    
    def draw_page_0(self):
        """Страница 0: Общая статистика"""
        y_offset = 50
        
        # Заголовок
        title = self.title_font.render("АНАЛИЗ ИГРОВОЙ СЕССИИ", True, YELLOW)
        self.screen.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, y_offset))
        y_offset += 60
        
        # Общая информация
        info = self.report['session_info']
        texts = [
            f"Финальный счет: {info['score']}",
            f"Длительность: {info['duration_sec']:.1f} секунд",
            "",
            "ЭФФЕКТИВНОСТЬ ДВИЖЕНИЯ:",
            f"  Всего ходов: {self.report['efficiency_metrics']['total_moves']}",
            f"  Ходов на еду: {self.report['efficiency_metrics']['moves_per_food']:.1f}",
            f"  Среднее расстояние до еды: {self.report['efficiency_metrics']['average_distance_to_food']:.1f}",
            "",
            "АНАЛИЗ ПУТЕЙ:",
            f"  Собрано еды: {self.report['path_analysis']['total_food_collected']}",
            f"  Средняя эффективность пути: {self.report['path_analysis']['average_path_efficiency']:.1f}%",
            "",
            "ПАТТЕРНЫ ДВИЖЕНИЯ:",
            f"  Смен направления: {self.report['movement_patterns']['direction_changes']}",
            f"  Смен на одну еду: {self.report['movement_patterns']['avg_changes_per_food']:.1f}",
        ]
        
        for text in texts:
            if text.startswith(" "):
                color = LIGHT_GRAY
                rendered = self.small_font.render(text, True, color)
            elif ":" in text and not text.endswith(":"):
                color = WHITE
                rendered = self.font.render(text, True, color)
            elif text == "":
                y_offset += 10
                continue
            else:
                color = GREEN
                rendered = self.font.render(text, True, color)
            
            self.screen.blit(rendered, (50, y_offset))
            y_offset += 30
    
    def draw_page_1(self):
        """Страница 1: Детальный анализ путей"""
        y_offset = 50
        
        title = self.title_font.render("ДЕТАЛЬНЫЙ АНАЛИЗ ПУТЕЙ", True, YELLOW)
        self.screen.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, y_offset))
        y_offset += 60
        
        paths = self.report['path_analysis']['paths'][:8]  # Первые 8 путей
        
        if not paths:
            text = self.font.render("Недостаточно данных для анализа", True, RED)
            self.screen.blit(text, (50, y_offset))
            return
        
        text = self.font.render(f"Показано первых {len(paths)} из {len(self.report['path_analysis']['paths'])} путей:", True, WHITE)
        self.screen.blit(text, (50, y_offset))
        y_offset += 40
        
        for i, path_data in enumerate(paths):
            actual = path_data['actual_length']
            optimal = path_data['optimal_length']
            
            if optimal != float('inf'):
                efficiency = (optimal / actual) * 100
                extra_moves = actual - optimal
                
                color = GREEN if efficiency > 80 else (YELLOW if efficiency > 60 else RED)
                
                text = f"Еда #{i+1}:  {actual} шагов  (оптимально: {optimal})  -  {efficiency:.0f}%  (+{extra_moves} лишних)"
            else:
                color = RED
                text = f"Еда #{i+1}:  {actual} шагов  (оптимальный путь не найден)"
            
            rendered = self.small_font.render(text, True, color)
            self.screen.blit(rendered, (50, y_offset))
            y_offset += 28
        
        # Рекомендации
        y_offset += 20
        avg_eff = self.report['path_analysis']['average_path_efficiency']
        
        recommendations = self.title_font.render("РЕКОМЕНДАЦИИ:", True, YELLOW)
        self.screen.blit(recommendations, (50, y_offset))
        y_offset += 40
        
        if avg_eff > 85:
            texts = [
                "Отличная эффективность! Вы выбираете близкие к оптимальным пути.",
                "Продолжайте планировать движения заранее."
            ]
            color = GREEN
        elif avg_eff > 70:
            texts = [
                "Хорошая эффективность, но есть куда расти.",
                "Старайтесь меньше петлять и выбирать более прямые маршруты."
            ]
            color = YELLOW
        else:
            texts = [
                "Много лишних движений. Планируйте путь заранее!",
                "Избегайте резких изменений направления без необходимости."
            ]
            color = RED
        
        for text in texts:
            rendered = self.small_font.render(text, True, color)
            self.screen.blit(rendered, (50, y_offset))
            y_offset += 30
    
    def draw_navigation(self):
        """Отрисовка навигации"""
        nav_text = self.small_font.render(
            f"Страница {self.current_page + 1}/{self.max_pages} | ← → для навигации | Q для выхода | I для изображений",
            True, GRAY
        )
        self.screen.blit(nav_text, (WINDOW_WIDTH // 2 - nav_text.get_width() // 2, WINDOW_HEIGHT - 30))
    
    def handle_events(self):
        """Обработка событий"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
                    return False
                elif event.key == pygame.K_LEFT:
                    self.current_page = max(0, self.current_page - 1)
                elif event.key == pygame.K_RIGHT:
                    self.current_page = min(self.max_pages - 1, self.current_page + 1)
                elif event.key == pygame.K_i:
                    return 'show_images'
        
        return True
    
    def run(self):
        """Главный цикл визуализатора"""
        running = True
        
        while running:
            result = self.handle_events()
            
            if result == False:
                running = False
            elif result == 'show_images':
                self.show_saved_images()
            
            self.screen.fill(BLACK)
            
            if self.current_page == 0:
                self.draw_page_0()
            elif self.current_page == 1:
                self.draw_page_1()
            
            self.draw_navigation()
            
            pygame.display.flip()
            self.clock.tick(30)
        
        pygame.quit()
    
    def show_saved_images(self):
        """Показать сохраненные изображения анализа"""
        import os
        
        images = [
            'analysis/path_comparison.png',
            'analysis/movement_heatmap.png'
        ]
        
        for img_path in images:
            if os.path.exists(img_path):
                try:
                    img = pygame.image.load(img_path)
                    
                    # Масштабируем если нужно
                    img_rect = img.get_rect()
                    if img_rect.width > WINDOW_WIDTH or img_rect.height > WINDOW_HEIGHT:
                        scale_x = WINDOW_WIDTH / img_rect.width
                        scale_y = WINDOW_HEIGHT / img_rect.height
                        scale = min(scale_x, scale_y) * 0.9
                        
                        new_width = int(img_rect.width * scale)
                        new_height = int(img_rect.height * scale)
                        img = pygame.transform.scale(img, (new_width, new_height))
                    
                    # Показываем изображение
                    showing = True
                    while showing:
                        for event in pygame.event.get():
                            if event.type == pygame.QUIT:
                                return
                            if event.type == pygame.KEYDOWN:
                                showing = False
                        
                        self.screen.fill(BLACK)
                        img_rect = img.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))
                        self.screen.blit(img, img_rect)
                        
                        text = self.small_font.render("Нажмите любую клавишу для продолжения", True, WHITE)
                        self.screen.blit(text, (WINDOW_WIDTH // 2 - text.get_width() // 2, WINDOW_HEIGHT - 30))
                        
                        pygame.display.flip()
                        self.clock.tick(30)
                
                except Exception as e:
                    print(f"Ошибка загрузки изображения {img_path}: {e}")
