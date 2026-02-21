"""
ML-анализатор траекторий змейки
"""
import json
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import pairwise_distances
import heapq


class PathAnalyzer:
    def __init__(self, session_file):
        """Инициализация анализатора"""
        with open(session_file, 'r') as f:
            self.session = json.load(f)
        
        self.data = self.session['data']
        self.score = self.session['score']
        self.duration = self.session['duration']
    
    def calculate_efficiency(self):
        """Расчет эффективности движения"""
        total_distance = 0
        direct_distances = []
        
        for i in range(len(self.data) - 1):
            # Реальное расстояние (сколько клеток прошли)
            head_curr = self.data[i]['snake_head']
            head_next = self.data[i + 1]['snake_head']
            
            if head_curr != head_next:
                total_distance += 1
            
            # Манхэттенское расстояние до еды
            direct_distances.append(self.data[i]['distance_to_food'])
        
        # Среднее расстояние до еды
        avg_distance_to_food = np.mean(direct_distances)
        
        # Время на одну еду
        time_per_food = self.duration / max(self.score, 1)
        
        return {
            'total_moves': total_distance,
            'average_distance_to_food': avg_distance_to_food,
            'time_per_food': time_per_food,
            'moves_per_food': total_distance / max(self.score, 1)
        }
    
    def find_optimal_paths(self):
        """Поиск оптимальных путей к еде (A*)"""
        food_events = []
        
        # Находим моменты когда змейка съела еду
        for i in range(len(self.data) - 1):
            if self.data[i]['score'] < self.data[i + 1]['score']:
                food_events.append({
                    'frame': i,
                    'start_pos': tuple(self.data[i]['snake_head']),
                    'food_pos': tuple(self.data[i]['food_position']),
                    'snake_body': set(tuple(pos) for pos in self.data[i]['snake_body']),
                    'actual_path': self._extract_path(i)
                })
        
        optimal_paths = []
        for event in food_events:
            optimal_path = self._astar(
                event['start_pos'],
                event['food_pos'],
                event['snake_body']
            )
            optimal_paths.append({
                'actual': event['actual_path'],
                'optimal': optimal_path,
                'actual_length': len(event['actual_path']),
                'optimal_length': len(optimal_path) if optimal_path else float('inf')
            })
        
        return optimal_paths
    
    def _extract_path(self, start_frame):
        """Извлечь реальный путь до следующей еды"""
        path = [tuple(self.data[start_frame]['snake_head'])]
        
        for i in range(start_frame + 1, len(self.data)):
            current_head = tuple(self.data[i]['snake_head'])
            if current_head != path[-1]:
                path.append(current_head)
            
            # Если съели еду, останавливаемся
            if i < len(self.data) - 1 and self.data[i]['score'] < self.data[i + 1]['score']:
                break
        
        return path
    
    def _astar(self, start, goal, obstacles):
        """A* алгоритм поиска пути"""
        def heuristic(pos):
            return abs(pos[0] - goal[0]) + abs(pos[1] - goal[1])
        
        def get_neighbors(pos):
            x, y = pos
            neighbors = []
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                new_x, new_y = x + dx, y + dy
                if (0 <= new_x < 40 and 0 <= new_y < 30 and 
                    (new_x, new_y) not in obstacles):
                    neighbors.append((new_x, new_y))
            return neighbors
        
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
                if neighbor not in closed_set:
                    new_cost = cost + 1
                    new_path = path + [neighbor]
                    priority = new_cost + heuristic(neighbor)
                    heapq.heappush(open_set, (priority, new_cost, neighbor, new_path))
        
        return None  # Путь не найден
    
    def analyze_movement_patterns(self):
        """Анализ паттернов движения"""
        directions = []
        direction_changes = 0
        
        for i in range(len(self.data) - 1):
            dir_curr = self.data[i]['direction']
            dir_next = self.data[i + 1]['direction']
            
            directions.append(dir_curr)
            
            if dir_curr != dir_next:
                direction_changes += 1
        
        # Подсчет использования направлений
        direction_counts = {
            (0, -1): 0,  # UP
            (0, 1): 0,   # DOWN
            (-1, 0): 0,  # LEFT
            (1, 0): 0    # RIGHT
        }
        
        for d in directions:
            direction_counts[tuple(d)] += 1
        
        return {
            'direction_changes': direction_changes,
            'direction_distribution': direction_counts,
            'avg_changes_per_food': direction_changes / max(self.score, 1)
        }
    
    def generate_report(self):
        """Генерация полного отчета"""
        efficiency = self.calculate_efficiency()
        optimal_paths = self.find_optimal_paths()
        movement = self.analyze_movement_patterns()
        
        # Расчет эффективности путей
        path_efficiency = []
        for path_data in optimal_paths:
            if path_data['optimal_length'] != float('inf'):
                efficiency_ratio = path_data['optimal_length'] / path_data['actual_length']
                path_efficiency.append(efficiency_ratio)
        
        avg_path_efficiency = np.mean(path_efficiency) if path_efficiency else 0
        
        report = {
            'session_info': {
                'score': self.score,
                'duration_ms': self.duration,
                'duration_sec': self.duration / 1000
            },
            'efficiency_metrics': efficiency,
            'path_analysis': {
                'total_food_collected': len(optimal_paths),
                'average_path_efficiency': avg_path_efficiency * 100,  # В процентах
                'paths': optimal_paths
            },
            'movement_patterns': movement
        }
        
        return report
    
    def visualize_paths(self, output_file='analysis/path_comparison.png'):
        """Визуализация сравнения путей"""
        optimal_paths = self.find_optimal_paths()
        
        # Берем первые 4 пути для визуализации
        num_plots = min(4, len(optimal_paths))
        
        if num_plots == 0:
            print("Нет данных для визуализации")
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        axes = axes.flatten()
        
        for i in range(num_plots):
            ax = axes[i]
            path_data = optimal_paths[i]
            
            actual_path = np.array(path_data['actual'])
            optimal_path = np.array(path_data['optimal']) if path_data['optimal'] else None
            
            # Рисуем сетку
            ax.set_xlim(-1, 41)
            ax.set_ylim(-1, 31)
            ax.set_aspect('equal')
            ax.grid(True, alpha=0.3)
            ax.invert_yaxis()
            
            # Реальный путь
            if len(actual_path) > 0:
                ax.plot(actual_path[:, 0], actual_path[:, 1], 
                       'b-o', linewidth=2, markersize=4, label='Ваш путь', alpha=0.6)
                ax.plot(actual_path[0, 0], actual_path[0, 1], 
                       'go', markersize=10, label='Старт')
                ax.plot(actual_path[-1, 0], actual_path[-1, 1], 
                       'ro', markersize=10, label='Еда')
            
            # Оптимальный путь
            if optimal_path is not None and len(optimal_path) > 0:
                ax.plot(optimal_path[:, 0], optimal_path[:, 1], 
                       'r--', linewidth=2, alpha=0.8, label='Оптимальный путь')
            
            efficiency = (path_data['optimal_length'] / path_data['actual_length'] * 100 
                         if path_data['optimal_length'] != float('inf') else 0)
            
            ax.set_title(f'Еда #{i+1}\n'
                        f'Ваш путь: {path_data["actual_length"]} шагов\n'
                        f'Оптимальный: {path_data["optimal_length"]} шагов\n'
                        f'Эффективность: {efficiency:.1f}%')
            ax.legend(loc='upper right', fontsize=8)
        
        # Скрываем неиспользуемые графики
        for i in range(num_plots, 4):
            axes[i].axis('off')
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"Визуализация сохранена: {output_file}")
    
    def visualize_heatmap(self, output_file='analysis/movement_heatmap.png'):
        """Тепловая карта движения змейки"""
        grid = np.zeros((30, 40))
        
        for frame in self.data:
            x, y = frame['snake_head']
            grid[y, x] += 1
        
        plt.figure(figsize=(12, 8))
        plt.imshow(grid, cmap='hot', interpolation='nearest')
        plt.colorbar(label='Частота посещения')
        plt.title('Тепловая карта движения змейки')
        plt.xlabel('X координата')
        plt.ylabel('Y координата')
        
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"Тепловая карта сохранена: {output_file}")
    
    def print_summary(self):
        """Вывести краткую сводку в консоль"""
        report = self.generate_report()
        
        print("\n" + "="*60)
        print("АНАЛИЗ ИГРОВОЙ СЕССИИ")
        print("="*60)
        
        print(f"\n📊 Общая информация:")
        print(f"   Счет: {report['session_info']['score']}")
        print(f"   Длительность: {report['session_info']['duration_sec']:.1f} сек")
        
        print(f"\n🎯 Эффективность движения:")
        print(f"   Всего ходов: {report['efficiency_metrics']['total_moves']}")
        print(f"   Ходов на еду: {report['efficiency_metrics']['moves_per_food']:.1f}")
        print(f"   Среднее расстояние до еды: {report['efficiency_metrics']['average_distance_to_food']:.1f}")
        
        print(f"\n🛣️  Анализ путей:")
        print(f"   Съедено еды: {report['path_analysis']['total_food_collected']}")
        print(f"   Средняя эффективность пути: {report['path_analysis']['average_path_efficiency']:.1f}%")
        
        print(f"\n🎮 Паттерны движения:")
        print(f"   Смен направления: {report['movement_patterns']['direction_changes']}")
        print(f"   Смен на еду: {report['movement_patterns']['avg_changes_per_food']:.1f}")
        
        print("\n" + "="*60)
