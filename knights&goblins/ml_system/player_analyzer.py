import json
import os
from datetime import datetime
import pandas as pd

class PlayerAnalyzer:
    def __init__(self, log_file="data/player_actions.json"):
        self.log_file = log_file
        self._ensure_log_file_exists()

    def _ensure_log_file_exists(self):
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w') as f:
                json.dump([], f) # Initialize with an empty list

    def log_action(self, action_type, player_state, level_state, timestamp=None):
        if timestamp is None:
            timestamp = datetime.now().isoformat()

        action_data = {
            "timestamp": timestamp,
            "action_type": action_type,
            "player_state": {
                "x": player_state.x,
                "y": player_state.y,
                "health": player_state.health,
                "velocity_x": player_state.velocity_x,
                "velocity_y": player_state.velocity_y,
                "on_ground": player_state.on_ground
            },
            "level_state": {
                "platforms": [{
                    "x": p.x, "y": p.y, "width": p.width, "height": p.height
                } for p in level_state.platforms],
                "enemies": [{
                    "x": e.x, "y": e.y, "width": e.width, "height": e.height, "health": e.health
                } for e in level_state.enemies if e.is_alive()]
            }
        }
        try:
            with open(self.log_file, 'r+') as f:
                file_data = json.load(f)
                file_data.append(action_data)
                f.seek(0)
                json.dump(file_data, f, indent=4)
        except json.JSONDecodeError:
            # Handle case where file might be empty or corrupted
            with open(self.log_file, 'w') as f:
                json.dump([action_data], f, indent=4)

    def analyze_data(self):
        try:
            with open(self.log_file, 'r') as f:
                data = json.load(f)
            df = pd.DataFrame(data)
            # Пример анализа: подсчет количества прыжков
            jump_actions = df[df['action_type'] == 'jump']
            st.write(f"Всего прыжков: {len(jump_actions)}")
            return df
        except FileNotFoundError:
            st.write("Файл логов не найден.")
            return pd.DataFrame()
        except json.JSONDecodeError:
            st.write("Ошибка чтения файла логов. Файл может быть поврежден или пуст.")
            return pd.DataFrame()

    def get_player_performance(self, df):
        if df.empty:
            return {"time_taken": 0, "deaths": 0, "jumps": 0}

        # Пример метрик производительности
        # Для реальной игры потребуется более сложная логика
        time_taken = (pd.to_datetime(df['timestamp'].iloc[-1]) - pd.to_datetime(df['timestamp'].iloc[0])).total_seconds()
        deaths = df[df['action_type'] == 'death'].shape[0]
        jumps = df[df['action_type'] == 'jump'].shape[0]

        return {"time_taken": time_taken, "deaths": deaths, "jumps": jumps}



