import streamlit as st
import time
import json
import os
from PIL import Image
import base64
from io import BytesIO

# Импорт игровых компонентов
from game_engine.game_controller import GameController
from ml_system.player_analyzer import PlayerAnalyzer
from ml_system.level_generator import LevelGenerator
import config

# Настройка страницы
st.set_page_config(
    page_title=config.GAME_TITLE,
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Заголовок игры
st.title(config.GAME_TITLE)
st.markdown("---")

# Функция для загрузки и кэширования спрайтов
@st.cache_resource
def load_backgrounds():
    backgrounds = {}
    try:
        for bg_name, bg_path in config.PATHS["backgrounds"].items():
            try:
                image = Image.open(bg_path)
                backgrounds[bg_name] = image
            except FileNotFoundError:
                st.warning(f"Фон {bg_name} не найден по пути {bg_path}")
                # Создаем заглушку для фона
                image = Image.new('RGB', (800, 500), (100, 100, 150))
                backgrounds[bg_name] = image
        return backgrounds
    except Exception as e:
        st.error(f"Ошибка при загрузке фонов: {e}")
        return {}
def load_sprites():
    sprites = {}
    try:
        for sprite_name, sprite_path in config.PATHS["sprites"].items():
            try:
                image = Image.open(sprite_path)
                # Проверяем наличие папки для спрайта
                if not os.path.exists(os.path.dirname(sprite_path)):
                    os.makedirs(os.path.dirname(sprite_path), exist_ok=True)
                sprites[sprite_name] = image.resize((50, 50))
            except FileNotFoundError:
                st.warning(f"Спрайт {sprite_name} не найден по пути {sprite_path}")
                # Создаем заглушку для спрайта
                image = Image.new('RGBA', (50, 50), (255, 0, 0, 128))
                sprites[sprite_name] = image
        return sprites
    except Exception as e:
        st.error(f"Ошибка при загрузке спрайтов: {e}")
        return {}

# Функция для преобразования изображения в base64 для HTML
def get_image_base64(img):
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

# Инициализация игрового контроллера и ML-систем
if 'game_controller' not in st.session_state:
    st.session_state.game_controller = GameController()
if 'player_analyzer' not in st.session_state:
    st.session_state.player_analyzer = PlayerAnalyzer(log_file=config.PATHS["player_actions"])
if 'level_generator' not in st.session_state:
    st.session_state.level_generator = LevelGenerator()
if 'sprites' not in st.session_state:
    st.session_state.sprites = load_sprites()
if 'backgrounds' not in st.session_state:
    st.session_state.backgrounds = load_backgrounds()
# Создаем игровой контейнер
game_container = st.empty()

# Sidebar для управления и информации
with st.sidebar:
    st.header("Управление")
    if st.button("Новая игра"):
        st.session_state.game_controller.initialize_game()
        st.experimental_rerun()
    
    if st.button("Сохранить игру"):
        st.session_state.game_controller.save_game_state()
        st.success("Игра сохранена!")
    
    st.header("Настройки уровня")
    difficulty_options = ["easy", "medium", "hard"]
    selected_difficulty = st.selectbox("Сложность:", difficulty_options, index=difficulty_options.index(st.session_state.game_controller.current_difficulty))
    
    if st.button("Сгенерировать новый уровень"):
        level_data = st.session_state.level_generator.generate_level(selected_difficulty)
        level_data["level_id"] = f"level_{st.session_state.game_controller.level_number}"
        level_data["difficulty"] = selected_difficulty
        st.session_state.game_controller.load_level(level_data)
        st.experimental_rerun()
    
    st.header("Информация об игроке")
    controller = st.session_state.game_controller
    if controller.player:
        st.write(f"Здоровье: {controller.player.health}/{controller.player.max_health}")
        st.write(f"Монеты: {controller.player.coins}")
        st.write(f"Очки: {controller.score}")
        st.write(f"Жизни: {controller.lives}")
        st.write(f"Уровень: {controller.level_number}")
        st.write(f"Сложность: {controller.current_difficulty}")
        
        # Прогресс бар здоровья
        st.progress(controller.player.health / controller.player.max_health)
    
    st.header("Управление с клавиатуры")
    st.write("⬅️ / ➡️ - Движение влево/вправо")
    st.write("⬆️ - Прыжок (дважды для двойного прыжка)")
    st.write("Space - Атака")
    st.write("Shift - Рывок")

# Обработка ввода с мобильных устройств
control_cols = st.columns([1, 1, 1, 1])
with control_cols[0]:
    if st.button("⬅️", key="mobile_left_btn"):
        st.session_state.game_controller.player.move_left()
        st.session_state.player_analyzer.log_action("move_left", st.session_state.game_controller.player, st.session_state.game_controller.level)
with control_cols[1]:
    if st.button("➡️", key="mobile_right_btn"):
        st.session_state.game_controller.player.move_right()
        st.session_state.player_analyzer.log_action("move_right", st.session_state.game_controller.player, st.session_state.game_controller.level)
with control_cols[2]:
    if st.button("⬆️", key="mobile_jump_btn"):
        if st.session_state.game_controller.player.jump():
            st.session_state.player_analyzer.log_action("jump", st.session_state.game_controller.player, st.session_state.game_controller.level)
with control_cols[3]:
    if st.button("⚔️", key="mobile_attack_btn"):
        if st.session_state.game_controller.player.attack():
            st.session_state.player_analyzer.log_action("attack", st.session_state.game_controller.player, st.session_state.game_controller.level)

# Обновляем состояние игры
controller = st.session_state.game_controller
controller.update()

# Отображаем игровое поле
with game_container.container():
    # Информация о текущем состоянии игры
    st.write(f"Здоровье: {controller.player.health} | Монеты: {controller.player.coins} | Очки: {controller.score} | Жизни: {controller.lives}")
    level_type = controller.level.level_type
    background_key = config.LEVEL_TYPES[level_type]["background"]
    # Статус уровня
    if controller.level_completed:
        st.success("🎉 Уровень пройден! 🎉")
        if st.button("Следующий уровень"):
            controller.level_number += 1
            level_data = st.session_state.level_generator.generate_level(controller.current_difficulty)
            level_data["level_id"] = f"level_{controller.level_number}"
            controller.load_level(level_data)
            st.experimental_rerun()
    # Берем фоновое изображение из кэша или используем цвет по умолчанию
    if background_key in st.session_state.backgrounds:
        bg_image = st.session_state.backgrounds[background_key]
        bg_base64 = get_image_base64(bg_image.resize((config.SCREEN_WIDTH, config.SCREEN_HEIGHT)))
        game_area_html = f"""
        <div style="position: relative; width: {config.SCREEN_WIDTH}px; height: {config.SCREEN_HEIGHT}px; 
                 border: 2px solid #333; overflow: hidden;">
            <img src="data:image/png;base64,{bg_base64}" 
                 style="position: absolute; left: 0; top: 0; width: 100%; height: 100%; object-fit: cover;">
        """
    else:
        # Запасной вариант, если фон не найден
        game_area_html = f"""
        <div style="position: relative; width: {config.SCREEN_WIDTH}px; height: {config.SCREEN_HEIGHT}px; 
                 border: 2px solid #333; background-color: #87CEEB; overflow: hidden;">
        """
    if controller.game_over:
        st.error("😢 Игра окончена! 😢")
        if st.button("Начать заново"):
            controller.initialize_game()
            st.experimental_rerun()
    
    # Визуализация игрового мира с использованием HTML/CSS
    game_area_html = f"""
    <div style="position: relative; width: {config.SCREEN_WIDTH}px; height: {config.SCREEN_HEIGHT}px; 
               border: 2px solid #333; background-color: #87CEEB; overflow: hidden;">
    """
    
    # Отображение платформ
    for platform in controller.level.platforms:
        platform_color = "#228B22"  # Обычная платформа
        if hasattr(platform, 'destructible') and platform.destructible:
            platform_color = "#A0522D"  # Разрушаемая платформа
        
        game_area_html += f"""
        <div style="position: absolute; left: {platform.x}px; top: {platform.y}px; 
                   width: {platform.width}px; height: {platform.height}px; 
                   background-color: {platform_color};">
        </div>
        """
    
    # Отображение ловушек
    for trap in controller.level.traps:
        trap_color = "#FF0000" if trap.is_active() else "#880000"
        game_area_html += f"""
        <div style="position: absolute; left: {trap.x}px; top: {trap.y}px; 
                   width: {trap.width}px; height: {trap.height}px; 
                   background-color: {trap_color};">
        </div>
        """
    
    # Отображение коллекционных предметов
    for collectible in controller.level.collectibles:
        if not collectible.is_collected():
            collectible_sprite = st.session_state.sprites.get(collectible.type, None)
            if collectible_sprite:
                collectible_base64 = get_image_base64(collectible_sprite)
                game_area_html += f"""
                <img src="data:image/png;base64,{collectible_base64}" 
                     style="position: absolute; left: {collectible.x}px; top: {collectible.y}px; 
                            width: {collectible.width}px; height: {collectible.height}px;">
                """
            else:
                # Цвет по умолчанию, если спрайт не найден
                collectible_color = config.COLLECTIBLE_TYPES.get(collectible.type, {}).get("color", "gold")
                game_area_html += f"""
                <div style="position: absolute; left: {collectible.x}px; top: {collectible.y}px; 
                           width: {collectible.width}px; height: {collectible.height}px; 
                           background-color: {collectible_color}; border-radius: 50%;">
                </div>
                """
    
    # Отображение врагов
    for enemy in controller.level.enemies:
        if enemy.is_alive():
            enemy_sprite = st.session_state.sprites.get(enemy.enemy_type, None)
            if enemy_sprite:
                enemy_base64 = get_image_base64(enemy_sprite)
                game_area_html += f"""
                <img src="data:image/png;base64
