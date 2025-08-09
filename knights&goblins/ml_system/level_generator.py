import random
import pickle
import os
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import numpy as np

class LevelGenerator:
    def __init__(self, model_path="ml_system/models/level_difficulty_model.pkl"):
        self.model_path = model_path
        self.model = self._load_or_create_model()
        self.scaler = StandardScaler()
        self.training_data = [] # [(features, difficulty_label)]

    def _load_or_create_model(self):
        if os.path.exists(self.model_path):
            with open(self.model_path, 'rb') as f:
                return pickle.load(f)
        else:
            # Создаем простую модель, если нет сохраненной
            # В реальной игре потребуется больше данных для обучения
            model = DecisionTreeClassifier()
            return model

    def _save_model(self):
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        with open(self.model_path, 'wb') as f:
            pickle.dump(self.model, f)

    def add_training_data(self, player_performance, difficulty_label):
        # player_performance: {"time_taken": float, "deaths": int, "jumps": int}
        features = [
            player_performance["time_taken"],
            player_performance["deaths"],
            player_performance["jumps"]
        ]
        self.training_data.append((features, difficulty_label))

    def train_model(self):
        if len(self.training_data) < 2: # Нужно хотя бы 2 примера для обучения
            print("Недостаточно данных для обучения модели.")
            return

        X = np.array([d[0] for d in self.training_data])
        y = np.array([d[1] for d in self.training_data])

        # Масштабирование признаков
        self.scaler.fit(X) # Fit scaler on all available data
        X_scaled = self.scaler.transform(X)

        X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)
        self.model.fit(X_train, y_train)
        self._save_model()
        print("Модель успешно обучена и сохранена.")

    def predict_difficulty(self, player_performance):
        if not self.training_data: # Если модель еще не обучена, возвращаем среднюю сложность
            return "medium"

        features = np.array([
            player_performance["time_taken"],
            player_performance["deaths"],
            player_performance["jumps"]
        ]).reshape(1, -1)

        # Масштабируем признаки с помощью обученного скейлера
        # Проверяем, был ли scaler обучен
        if hasattr(self.scaler, 'scale_'):
            features_scaled = self.scaler.transform(features)
        else:
            # Если scaler не обучен, используем его для обучения на текущих данных
            self.scaler.fit(features)
            features_scaled = self.scaler.transform(features)

        prediction = self.model.predict(features_scaled)
        return prediction[0]

    def generate_level(self, difficulty="medium"):
        platforms = []
        enemies = []
        start_x = 50
        start_y = 400
        end_x = 750

        # Базовые платформы
        platforms.append({"x": 0, "y": 450, "width": 800, "height": 50})

        if difficulty == "easy":
            # Простой уровень: несколько платформ, мало врагов
            num_platforms = random.randint(3, 5)
            num_enemies = random.randint(0, 1)
            min_platform_width = 100
            max_platform_width = 200
            min_platform_height = 20
            max_platform_height = 40
            min_gap = 50
            max_gap = 150

        elif difficulty == "medium":
            # Средний уровень: больше платформ, больше врагов, возможно, пропасти
            num_platforms = random.randint(5, 8)
            num_enemies = random.randint(1, 3)
            min_platform_width = 80
            max_platform_width = 150
            min_platform_height = 20
            max_platform_height = 40
            min_gap = 80
            max_gap = 200

        elif difficulty == "hard":
            # Сложный уровень: много платформ, движущиеся платформы, много врагов, узкие проходы
            num_platforms = random.randint(7, 10)
            num_enemies = random.randint(3, 5)
            min_platform_width = 50
            max_platform_width = 120
            min_platform_height = 20
            max_platform_height = 40
            min_gap = 100
            max_gap = 250

        # Генерация платформ
        current_x = start_x
        for _ in range(num_platforms):
            width = random.randint(min_platform_width, max_platform_width)
            height = random.randint(min_platform_height, max_platform_height)
            x = current_x + random.randint(min_gap, max_gap)
            y = random.randint(200, 400) # Высота платформ
            platforms.append({"x": x, "y": y, "width": width, "height": height})
            current_x = x + width

        # Генерация врагов
        for _ in range(num_enemies):
            # Размещаем врагов на существующих платформах или на земле
            platform_to_spawn_on = random.choice(platforms)
            enemy_x = random.randint(platform_to_spawn_on["x"], platform_to_spawn_on["x"] + platform_to_spawn_on["width"] - 50)
            enemy_y = platform_to_spawn_on["y"] - 50 # Над платформой
            enemies.append({"x": enemy_x, "y": enemy_y, "width": 50, "height": 50})

        return {
            "start_x": start_x,
            "start_y": start_y,
            "end_x": end_x,
            "platforms": platforms,
            "enemies": enemies
        }


