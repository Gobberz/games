"""
AI-агент для игры в змейку
"""
import heapq
from game.config import *


class SnakeAI:
    def __init__(self, snake, food):
        """Инициализация AI"""
        self.snake = snake
        self.food = food
    
    def get_next_move(self):
        """Получить следующий ход AI"""
        path = self.find_path_to_food()
        
        if path and len(path) > 1:
            # Получаем следующую позицию
            current = self.snake.get_head()
            next_pos = path[1]
            
            # Определяем направление
            dx = next_pos[0] - current[0]
            dy = next_pos[1] - current[1]
            
            return (dx, dy)
        
        # Если путь не найден, двигаемся безопасно
        return self.get_safe_direction()
    
    def find_path_to_food(self):
        """Поиск пути к еде используя A*"""
        start = self.snake.get_head()
        goal = self.food.position
        obstacles = set(self.snake.body[1:])  # Тело змейки (без головы)
        
        def heuristic(pos):
            return abs(pos[0] - goal[0]) + abs(pos[1] - goal[1])
        
        def get_neighbors(pos):
            x, y = pos
            neighbors = []
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                new_x, new_y = x + dx, y + dy
                if (0 <= new_x < GRID_WIDTH and 0 <= new_y < GRID_HEIGHT):
                    neighbors.append((new_x, new_y))
            return neighbors
        
        def is_safe(pos):
            """Проверка безопасности позиции"""
            if pos in obstacles:
                return False
            
            # Дополнительная проверка: есть ли выход из этой позиции
            safe_neighbors = 0
            for neighbor in get_neighbors(pos):
                if neighbor not in obstacles:
                    safe_neighbors += 1
            
            return safe_neighbors > 0
        
        open_set = [(heuristic(start), 0, start, [start])]
        closed_set = set()
        
        while open_set:
            _, cost, current, path = heapq.heappop(open_set)
            
            if current == goal:
                return path
            
            if current in closed_set:
                continue
            
            closed_set.add(current)
            
            for neighbor in get_neighbors(current):
                if neighbor not in closed_set and is_safe(neighbor):
                    new_cost = cost + 1
                    new_path = path + [neighbor]
                    priority = new_cost + heuristic(neighbor)
                    heapq.heappush(open_set, (priority, new_cost, neighbor, new_path))
        
        return None
    
    def get_safe_direction(self):
        """Получить безопасное направление если путь не найден"""
        head = self.snake.get_head()
        obstacles = set(self.snake.body)
        
        # Приоритет направлений (пытаемся сохранить текущее)
        current_dir = self.snake.direction
        directions = [current_dir, UP, DOWN, LEFT, RIGHT]
        
        for direction in directions:
            dx, dy = direction
            new_pos = (head[0] + dx, head[1] + dy)
            
            # Проверяем что позиция безопасна
            if (0 <= new_pos[0] < GRID_WIDTH and 
                0 <= new_pos[1] < GRID_HEIGHT and 
                new_pos not in obstacles):
                
                # Дополнительная проверка: не ведет ли это в тупик
                if self.has_escape_route(new_pos, obstacles):
                    return direction
        
        # Если ничего не нашли, возвращаем текущее направление
        return current_dir
    
    def has_escape_route(self, position, obstacles):
        """Проверка наличия пути отступления из позиции"""
        x, y = position
        safe_neighbors = 0
        
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            new_x, new_y = x + dx, y + dy
            if (0 <= new_x < GRID_WIDTH and 
                0 <= new_y < GRID_HEIGHT and 
                (new_x, new_y) not in obstacles):
                safe_neighbors += 1
        
        return safe_neighbors > 0


class HybridAI(SnakeAI):
    """
    Гибридный AI который играет как человек, но с улучшениями
    """
    def __init__(self, snake, food, player_style=None):
        super().__init__(snake, food)
        self.player_style = player_style or {}
        self.aggression = self.player_style.get('aggression', 0.7)
    
    def get_next_move(self):
        """Получить следующий ход с учетом стиля игрока"""
        optimal_move = super().get_next_move()
        
        # С определенной вероятностью делаем оптимальный ход
        # Иначе имитируем менее эффективное поведение игрока
        import random
        
        if random.random() < self.aggression:
            return optimal_move
        else:
            # Делаем менее оптимальный, но безопасный ход
            return self.get_player_like_move()
    
    def get_player_like_move(self):
        """Ход похожий на человеческий стиль"""
        head = self.snake.get_head()
        food = self.food.position
        
        # Простое жадное движение к еде
        dx = 0 if head[0] == food[0] else (1 if food[0] > head[0] else -1)
        dy = 0 if head[1] == food[1] else (1 if food[1] > head[1] else -1)
        
        # Приоритет горизонтали или вертикали
        import random
        if dx != 0 and dy != 0:
            if random.random() < 0.5:
                direction = (dx, 0)
            else:
                direction = (0, dy)
        elif dx != 0:
            direction = (dx, 0)
        elif dy != 0:
            direction = (0, dy)
        else:
            direction = self.snake.direction
        
        # Проверяем безопасность
        new_pos = (head[0] + direction[0], head[1] + direction[1])
        if (0 <= new_pos[0] < GRID_WIDTH and 
            0 <= new_pos[1] < GRID_HEIGHT and 
            new_pos not in self.snake.body):
            return direction
        
        return self.get_safe_direction()
