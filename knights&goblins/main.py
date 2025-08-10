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
def load_sprites():
    sprites = {}
    sprite_sizes = {
        "coin": (25, 25),
        "health_potion": (30, 30),
        "key": (25, 25),
        # Остальные спрайты по умолчанию 50x50
    }
    
    try:
        for sprite_name, sprite_path in config.PATHS["sprites"].items():
            try:
                image = Image.open(sprite_path)
                # Используем специфические размеры или размер по умолчанию
                if sprite_name in sprite_sizes:
                    size = sprite_sizes[sprite_name]
                else:
                    size = (50, 50)
                sprites[sprite_name] = image.resize(size)
            except FileNotFoundError:
                st.warning(f"Спрайт {sprite_name} не найден по пути {sprite_path}")
                # Создаем заглушку для спрайта
                if sprite_name in sprite_sizes:
                    size = sprite_sizes[sprite_name]
                else:
                    size = (50, 50)
                image = Image.new('RGBA', size, (255, 0, 0, 128))
                sprites[sprite_name] = image
        return sprites
    except Exception as e:
        st.error(f"Ошибка при загрузке спрайтов: {e}")
        return {}

# Функция для загрузки и кэширования фоновых изображений
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
control_cols = st.columns([1, 1, 1, 1, 1])
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
with control_cols[4]:
    if st.button("⚡", key="mobile_dash_btn"):
        if st.session_state.game_controller.player.dash():
            st.session_state.player_analyzer.log_action("dash", st.session_state.game_controller.player, st.session_state.game_controller.level)

# Обновляем состояние игры
controller = st.session_state.game_controller
controller.update()

# Отображаем игровое поле
with game_container.container():
    # Информация о текущем состоянии игры
    st.write(f"Здоровье: {controller.player.health} | Монеты: {controller.player.coins} | Очки: {controller.score} | Жизни: {controller.lives}")
    
    # Статус уровня
    if controller.level_completed:
        st.success("🎉 Уровень пройден! 🎉")
        if st.button("Следующий уровень"):
            controller.level_number += 1
            level_data = st.session_state.level_generator.generate_level(controller.current_difficulty)
            level_data["level_id"] = f"level_{controller.level_number}"
            controller.load_level(level_data)
            st.experimental_rerun()
    
    if controller.game_over:
        st.error("😢 Игра окончена! 😢")
        if st.button("Начать заново"):
            controller.initialize_game()
            st.experimental_rerun()
    
    # Получаем тип уровня и фон
    level_type = controller.level.level_type
    background_key = config.LEVEL_TYPES[level_type]["background"]
    
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
    
    # Отображение платформ
    platform_color = config.LEVEL_TYPES.get(level_type, {}).get("platform_color", "#228B22")
    for platform in controller.level.platforms:
        platform_color_actual = "#A0522D" if hasattr(platform, 'destructible') and platform.destructible else platform_color
        
        game_area_html += f"""
        <div style="position: absolute; left: {platform.x}px; top: {platform.y}px; 
                   width: {platform.width}px; height: {platform.height}px; 
                   background-color: {platform_color_actual};">
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
                
                # Добавляем эффект блеска для монет
                if collectible.type == "coin" and hasattr(collectible, 'sparkle_visible') and collectible.sparkle_visible:
                    game_area_html += f"""
                    <div style="position: absolute; left: {collectible.x + 5}px; top: {collectible.y - 5}px; 
                              font-size: 12px; color: yellow;">✨</div>
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
                <img src="data:image/png;base64,{enemy_base64}" 
                     style="position: absolute; left: {enemy.x}px; top: {enemy.y}px; 
                            width: {enemy.width}px; height: {enemy.height}px;">
                """
            else:
                # Цвет по умолчанию, если спрайт не найден
                enemy_color = config.ENEMY_TYPES.get(enemy.enemy_type, {}).get("color", "red")
                game_area_html += f"""
                <div style="position: absolute; left: {enemy.x}px; top: {enemy.y}px; 
                           width: {enemy.width}px; height: {enemy.height}px; 
                           background-color: {enemy_color};">
                </div>
                """
            
            # Отображение полоски здоровья для врагов
            health_percentage = enemy.health / enemy.max_health
            game_area_html += f"""
            <div style="position: absolute; left: {enemy.x}px; top: {enemy.y - 10}px; 
                       width: {enemy.width}px; height: 5px; background-color: #FF0000;">
                <div style="width: {health_percentage * 100}%; height: 100%; background-color: #00FF00;"></div>
            </div>
            """
    
    # Отображение проектилей (стрелы лучников и т.д.)
    for enemy in controller.level.enemies:
        if hasattr(enemy, 'projectiles'):
            for projectile in enemy.projectiles:
                game_area_html += f"""
                <div style="position: absolute; left: {projectile['x']}px; top: {projectile['y']}px; 
                          width: {projectile['width']}px; height: {projectile['height']}px; 
                          background-color: yellow; border-radius: 50%;">
                </div>
                """
    
    # Отображение игрока
    player_sprite = st.session_state.sprites.get("knight", None)
    if player_sprite:
        player_base64 = get_image_base64(player_sprite)
        game_area_html += f"""
        <img src="data:image/png;base64,{player_base64}" 
             style="position: absolute; left: {controller.player.x}px; top: {controller.player.y}px; 
                    width: {controller.player.width}px; height: {controller.player.height}px; 
                    transform: scaleX({1 if controller.player.facing_right else -1});">
        """
    else:
        player_color = "blue"
        if controller.player.invulnerable:
            player_color = "rgba(0, 0, 255, 0.5)"  # Полупрозрачный синий для неуязвимости
            
        game_area_html += f"""
        <div style="position: absolute; left: {controller.player.x}px; top: {controller.player.y}px; 
                   width: {controller.player.width}px; height: {controller.player.height}px; 
                   background-color: {player_color};">
        </div>
        """
    
    # Отображение атаки игрока (если в данный момент атакует)
    if controller.player.is_attacking:
        attack_direction = 1 if controller.player.facing_right else -1
        attack_x = controller.player.x + (controller.player.width if attack_direction > 0 else -controller.player.attack_range)
        attack_width = controller.player.attack_range
        
        game_area_html += f"""
        <div style="position: absolute; left: {attack_x}px; top: {controller.player.y}px; 
                   width: {attack_width}px; height: {controller.player.height}px; 
                   background-color: rgba(255, 255, 0, 0.5); border: 1px solid yellow;">
        </div>
        """
    
    # Отображение дверей/выхода уровня
    game_area_html += f"""
    <div style="position: absolute; left: {controller.level.end_x - 20}px; top: {controller.level.end_y - 40}px; 
               width: 40px; height: 40px; background-color: rgba(0, 255, 0, 0.7); 
               border: 2px solid darkgreen; border-radius: 5px;">
        <div style="text-align: center; margin-top: 5px; font-weight: bold; color: white;">⚑</div>
    </div>
    """
    
    # Закрываем основной div
    game_area_html += "</div>"
    
    # Отображаем HTML на странице
    st.components.v1.html(game_area_html, height=config.SCREEN_HEIGHT + 10)
    
    # Показываем статистику уровня
    st.markdown("---")
    st.subheader("Статистика уровня")
    stats_cols = st.columns(4)
    
    with stats_cols[0]:
        st.write(f"Оставшиеся враги: {controller.level.get_remaining_enemies()}")
    with stats_cols[1]:
        st.write(f"Оставшиеся предметы: {controller.level.get_remaining_collectibles()}")
    with stats_cols[2]:
        st.write(f"Время на уровне: {controller.game_time:.1f} с")
    with stats_cols[3]:
        # Проверяем цели уровня
        collect_all = controller.level.objectives.get('collect_all', False)
        defeat_all = controller.level.objectives.get('defeat_all', False)
        
        objective_text = "Дойти до конца уровня"
        if collect_all:
            objective_text += ", собрать все предметы"
        if defeat_all:
            objective_text += ", победить всех врагов"
            
        st.write(f"Цель: {objective_text}")
