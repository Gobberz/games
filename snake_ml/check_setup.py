#!/usr/bin/env python3
"""
Скрипт проверки структуры проекта
"""
import os
import sys


def check_file(filepath, description):
    """Проверка существования файла"""
    exists = os.path.exists(filepath)
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {filepath}")
    return exists


def check_dependencies():
    """Проверка установленных зависимостей"""
    print("\n" + "="*60)
    print("ПРОВЕРКА ЗАВИСИМОСТЕЙ")
    print("="*60)
    
    deps = {
        'pygame': 'Игровой движок',
        'numpy': 'Численные вычисления',
        'matplotlib': 'Визуализация',
        'sklearn': 'Машинное обучение'
    }
    
    all_installed = True
    for module, description in deps.items():
        try:
            __import__(module)
            print(f"✅ {description} ({module})")
        except ImportError:
            print(f"❌ {description} ({module}) - НЕ УСТАНОВЛЕН")
            all_installed = False
    
    return all_installed


def check_structure():
    """Проверка структуры проекта"""
    print("\n" + "="*60)
    print("ПРОВЕРКА СТРУКТУРЫ ПРОЕКТА")
    print("="*60)
    
    files = [
        ("main.py", "Главный файл"),
        ("README.md", "Документация"),
        ("requirements.txt", "Зависимости"),
        ("game/__init__.py", "Пакет game"),
        ("game/config.py", "Конфигурация"),
        ("game/snake.py", "Класс змейки"),
        ("game/food.py", "Класс еды"),
        ("game/game.py", "Игровой цикл"),
        ("ml/__init__.py", "Пакет ML"),
        ("ml/analyzer.py", "Анализатор"),
        ("ml/ai_player.py", "AI игрок"),
        ("ml/ai_demo.py", "AI демо"),
        ("ml/visualizer.py", "Визуализатор"),
    ]
    
    all_exist = True
    for filepath, description in files:
        exists = check_file(filepath, description)
        all_exist = all_exist and exists
    
    return all_exist


def check_directories():
    """Проверка и создание директорий"""
    print("\n" + "="*60)
    print("ПРОВЕРКА ДИРЕКТОРИЙ")
    print("="*60)
    
    dirs = ['data', 'analysis']
    
    for directory in dirs:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✅ Создана директория: {directory}")
        else:
            print(f"✅ Директория существует: {directory}")


def print_summary(structure_ok, deps_ok):
    """Вывод итоговой сводки"""
    print("\n" + "="*60)
    print("ИТОГОВАЯ СВОДКА")
    print("="*60)
    
    if structure_ok and deps_ok:
        print("✅ Проект готов к запуску!")
        print("\nДля запуска введите:")
        print("    python main.py")
        print("\nили")
        print("    python3 main.py")
    elif structure_ok and not deps_ok:
        print("⚠️  Структура проекта в порядке, но не хватает зависимостей")
        print("\nУстановите зависимости:")
        print("    pip install -r requirements.txt")
        print("\nили")
        print("    pip install pygame numpy matplotlib scikit-learn")
    elif not structure_ok and deps_ok:
        print("⚠️  Зависимости установлены, но проблемы со структурой проекта")
        print("Проверьте отсутствующие файлы выше")
    else:
        print("❌ Обнаружены проблемы")
        print("\n1. Установите зависимости:")
        print("    pip install -r requirements.txt")
        print("\n2. Проверьте целостность файлов проекта")


def main():
    """Главная функция"""
    print("="*60)
    print("   ПРОВЕРКА ПРОЕКТА: ЗМЕЙКА С ML-АНАЛИЗОМ")
    print("="*60)
    
    # Проверяем директории
    check_directories()
    
    # Проверяем структуру
    structure_ok = check_structure()
    
    # Проверяем зависимости
    deps_ok = check_dependencies()
    
    # Итоговая сводка
    print_summary(structure_ok, deps_ok)
    
    # Возврат кода ошибки
    sys.exit(0 if (structure_ok and deps_ok) else 1)


if __name__ == "__main__":
    main()
