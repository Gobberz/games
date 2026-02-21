#!/usr/bin/env python3
"""
Змейка с ML-анализом
Главное меню и точка входа
"""
import sys
import os
import pygame
from game.config import *


def draw_menu(screen, font, title_font, selected_option):
    """Отрисовка главного меню"""
    screen.fill(BLACK)
    
    # Заголовок
    title = title_font.render("ЗМЕЙКА С ML-АНАЛИЗОМ", True, GREEN)
    screen.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, 100))
    
    # Опции меню
    options = [
        "1. Играть",
        "2. Посмотреть AI демо",
        "3. Анализировать последнюю игру",
        "4. Выход"
    ]
    
    y_offset = 250
    for i, option in enumerate(options):
        if i == selected_option:
            color = YELLOW
            text = font.render(f"> {option} <", True, color)
        else:
            color = WHITE
            text = font.render(option, True, color)
        
        screen.blit(text, (WINDOW_WIDTH // 2 - text.get_width() // 2, y_offset))
        y_offset += 60
    
    # Инструкции
    instructions = [
        "Управление: WASD или стрелки",
        "После игры нажмите SPACE для анализа",
        "Или R для перезапуска"
    ]
    
    small_font = pygame.font.Font(None, 20)
    y_offset = WINDOW_HEIGHT - 100
    for instruction in instructions:
        text = small_font.render(instruction, True, GRAY)
        screen.blit(text, (WINDOW_WIDTH // 2 - text.get_width() // 2, y_offset))
        y_offset += 25
    
    pygame.display.flip()


def main_menu():
    """Главное меню"""
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Змейка с ML - Главное меню")
    clock = pygame.time.Clock()
    
    font = pygame.font.Font(None, 36)
    title_font = pygame.font.Font(None, 48)
    
    selected_option = 0
    max_options = 3  # 0-3 индексы
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP or event.key == pygame.K_w:
                    selected_option = (selected_option - 1) % (max_options + 1)
                elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                    selected_option = (selected_option + 1) % (max_options + 1)
                elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    if selected_option == 0:
                        pygame.quit()
                        play_game()
                        # Возвращаемся в меню после игры
                        pygame.init()
                        screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
                    elif selected_option == 1:
                        pygame.quit()
                        ai_demo()
                        # Возвращаемся в меню
                        pygame.init()
                        screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
                    elif selected_option == 2:
                        pygame.quit()
                        analyze_last_game()
                        # Возвращаемся в меню
                        pygame.init()
                        screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
                    elif selected_option == 3:
                        running = False
                elif event.key == pygame.K_1:
                    pygame.quit()
                    play_game()
                    pygame.init()
                    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
                elif event.key == pygame.K_2:
                    pygame.quit()
                    ai_demo()
                    pygame.init()
                    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
                elif event.key == pygame.K_3:
                    pygame.quit()
                    analyze_last_game()
                    pygame.init()
                    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
                elif event.key == pygame.K_4 or event.key == pygame.K_ESCAPE:
                    running = False
        
        draw_menu(screen, font, title_font, selected_option)
        clock.tick(30)
    
    pygame.quit()
    sys.exit()


def play_game():
    """Запуск игры"""
    from game.game import Game
    
    game = Game()
    session_file = game.run()
    
    if session_file:
        # Игрок нажал SPACE для анализа
        from ml.analyzer import PathAnalyzer
        from ml.visualizer import AnalysisViewer
        
        print("\n🔍 Анализирую вашу игру...")
        analyzer = PathAnalyzer(session_file)
        
        # Генерируем визуализации
        analyzer.visualize_paths()
        analyzer.visualize_heatmap()
        
        # Печатаем сводку
        analyzer.print_summary()
        
        # Генерируем отчет
        report = analyzer.generate_report()
        
        # Показываем визуальный анализ
        print("\n📊 Открываю визуальный анализ...")
        viewer = AnalysisViewer(session_file, report)
        viewer.run()


def ai_demo():
    """Запуск AI демо"""
    from ml.ai_demo import AIDemo
    
    print("\n🤖 Запускаю AI демонстрацию...")
    print("AI будет играть оптимально. Синяя линия показывает планируемый путь.")
    print("Нажмите +/- для изменения скорости, Q для выхода.")
    
    demo = AIDemo(speed_multiplier=1.5)
    demo.run()


def analyze_last_game():
    """Анализ последней игры"""
    import glob
    from ml.analyzer import PathAnalyzer
    from ml.visualizer import AnalysisViewer
    
    # Находим последний файл сессии
    sessions = glob.glob('data/session_*.json')
    
    if not sessions:
        print("\n❌ Нет сохраненных игр для анализа!")
        print("Сначала сыграйте хотя бы одну игру.\n")
        input("Нажмите Enter для продолжения...")
        return
    
    latest_session = max(sessions, key=os.path.getctime)
    print(f"\n🔍 Анализирую игру: {latest_session}")
    
    analyzer = PathAnalyzer(latest_session)
    
    # Генерируем визуализации
    analyzer.visualize_paths()
    analyzer.visualize_heatmap()
    
    # Печатаем сводку
    analyzer.print_summary()
    
    # Генерируем отчет
    report = analyzer.generate_report()
    
    # Показываем визуальный анализ
    print("\n📊 Открываю визуальный анализ...")
    viewer = AnalysisViewer(latest_session, report)
    viewer.run()


if __name__ == "__main__":
    # Создаем необходимые директории
    os.makedirs('data', exist_ok=True)
    os.makedirs('analysis', exist_ok=True)
    
    print("="*60)
    print("       ЗМЕЙКА С ML-АНАЛИЗОМ")
    print("="*60)
    print()
    
    main_menu()
