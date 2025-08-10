"""
Константы и конфигурации для игры Knights & Goblins
"""

# Общие настройки игры
GAME_TITLE = "⚔️ Рыцарь против Гоблинов"
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 500
FPS = 60

# Настройки игрока
PLAYER_DEFAULT = {
    "width": 50,
    "height": 50,
    "speed": 5,
    "jump_strength": 10,
    "max_health": 100,
    "attack_damage": 20,
    "attack_cooldown": 1.0,  # в секундах
}

# Настройки врагов
ENEMY_TYPES = {
    "goblin": {
        "width": 50,
        "height": 50,
        "speed": 2,
        "health": 30,
        "damage": 10,
        "attack_range": 20,
        "detection_range": 200,
        "color": "red",
    },
    "archer": {
        "width": 50,
        "height": 50,
        "speed": 1,
        "health": 20,
        "damage": 15,
        "attack_range": 300,
        "detection_range": 350,
        "color": "darkred",
        "projectile_speed": 4,
    },
    "troll": {
        "width": 60,
        "height": 60,
        "speed": 1,
        "health": 60,
        "damage": 20,
        "attack_range": 30,
        "detection_range": 150,
        "color": "green",
    }
}

# Настройки физики
PHYSICS = {
    "gravity": 0.5,
    "friction": 0.8,
    "terminal_velocity": 15,
}

# Настройки уровней
LEVEL_SETTINGS = {
    "easy": {
        "num_platforms": (3, 5),  # (min, max)
        "num_enemies": (0, 2),
        "platform_width": (100, 200),
        "platform_height": (20, 40),
        "gap_range": (50, 150),
        "collectibles": (1, 3),
    },
    "medium": {
        "num_platforms": (5, 8),
        "num_enemies": (2, 4),
        "platform_width": (80, 150),
        "platform_height": (20, 40),
        "gap_range": (80, 200),
        "collectibles": (3, 5),
    },
    "hard": {
        "num_platforms": (7, 10),
        "num_enemies": (4, 7),
        "platform_width": (50, 120),
        "platform_height": (20, 40),
        "gap_range": (100, 250),
        "collectibles": (5, 8),
    }
}

# Настройки коллекционных предметов
COLLECTIBLE_TYPES = {
    "coin": {
        "width": 20,
        "height": 20,
        "value": 10,
        "color": "gold",
    },
    "health_potion": {
        "width": 25,
        "height": 25,
        "heal_amount": 20,
        "color": "pink",
    },
    "key": {
        "width": 25,
        "height": 25,
        "color": "silver",
    }
}

# Пути к файлам
PATHS = {
    "game_state": "data/game_state.json",
    "level_stats": "data/level_stats.json",
    "player_actions": "data/player_actions.json",
    "sprites": {
        "knight": "assets/sprites/knight.png",
        "goblin": "assets/sprites/goblin.png",
        "archer": "assets/sprites/archer.png",
        "troll": "assets/sprites/troll.png",
        "coin": "assets/sprites/coin.png",
        "health_potion": "assets/sprites/health_potion.png",
        "key": "assets/sprites/key.png",
    }
}
