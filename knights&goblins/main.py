import streamlit as st
from game_engine.player import Player
from game_engine.enemies import Goblin
from game_engine.level import Level, Platform
from game_engine.physics import Physics
from ml_system.player_analyzer import PlayerAnalyzer
from ml_system.level_generator import LevelGenerator
import time
import json
import os
from PIL import Image

# Настройка страницы
st.set_page_config(
    page_title="Рыцарь против Гоблинов",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Заголовок игры
st.title("⚔️ Рыцарь против Гоблинов")
st.markdown("---")

# Загрузка спрайтов
@st.cache_resource
def load_sprites():
    try:
        knight_img = Image.open("assets/sprites/knight.png").resize((50, 50))
        goblin_img = Image.open("assets/sprites/goblin.png").resize((50, 50))
        return knight_img, goblin_img
    except FileNotFoundError:
        st.error("Не найдены файлы спрайтов. Убедитесь, что они находятся в папке assets/sprites.")
        return None, None

knight_sprite, goblin_sprite = load_sprites()

# Инициализация ML-систем
if 'player_analyzer' not in st.session_state:
    st.session_state.player_analyzer = PlayerAnalyzer(log_file="data/player_actions.json")
if 'level_generator' not in st.session_state:
    st.session_state.level_generator = LevelGenerator(model_path="ml_system/models/level_difficulty_model.pkl")

# Инициализация игры
if 'player' not in st.session_state:
    st.session_state.player = Player(x=50, y=400, width=50, height=50)
if 'current_level_data' not in st.session_state:
    st.session_state.current_level_data = st.session_state.level_generator.generate_level("easy")
if 'level' not in st.session_state:
    st.session_state.level = Level(st.session_state.current_level_data)
if 'physics' not in st.session_state:
    st.session_state.physics = Physics()

# Игровой контейнер
game_container = st.empty()

# Функция для сброса уровня
def reset_level():
    st.session_state.player = Player(x=st.session_state.current_level_data["start_x"], y=st.session_state.current_level_data["start_y"], width=50, height=50)
    st.session_state.level = Level(st.session_state.current_level_data)
    st.session_state.game_start_time = time.time()
    st.session_state.deaths = st.session_state.get('deaths', 0)

# Функция для генерации нового уровня
def generate_new_level(difficulty):
    st.session_state.current_level_data = st.session_state.level_generator.generate_level(difficulty)
    reset_level()

# Инициализация времени начала игры для анализа производительности
if 'game_start_time' not in st.session_state:
    st.session_state.game_start_time = time.time()
if 'deaths' not in st.session_state:
    st.session_state.deaths = 0

# Sidebar для управления и информации
with st.sidebar:
    st.header("Управление")
    if st.button("Начать новую игру"):
        st.session_state.player = Player(x=50, y=400, width=50, height=50)
        st.session_state.current_level_data = st.session_state.level_generator.generate_level("easy")
        st.session_state.level = Level(st.session_state.current_level_data)
        st.session_state.game_start_time = time.time()
        st.session_state.deaths = 0
        st.session_state.player_analyzer._ensure_log_file_exists() # Очистка логов для новой игры
        st.experimental_rerun()

    st.header("Информация об игроке")
    st.write(f"Здоровье: {st.session_state.player.health}")
    st.write(f"Смертей: {st.session_state.deaths}")

    st.header("Управление уровнем")
    difficulty_options = ["easy", "medium", "hard"]
    selected_difficulty = st.selectbox("Выбрать сложность уровня:", difficulty_options)
    if st.button("Сгенерировать новый уровень"):
        generate_new_level(selected_difficulty)
        st.experimental_rerun()

    if st.button("Обучить ML модель"):
        df_actions = st.session_state.player_analyzer.analyze_data()
        if not df_actions.empty:
            player_performance = st.session_state.player_analyzer.get_player_performance(df_actions)
            if player_performance["deaths"] == 0 and player_performance["time_taken"] < 60:
                st.session_state.level_generator.add_training_data(player_performance, "easy")
            elif player_performance["deaths"] > 0 and player_performance["time_taken"] > 60:
                st.session_state.level_generator.add_training_data(player_performance, "hard")
            else:
                st.session_state.level_generator.add_training_data(player_performance, "medium")

            st.session_state.level_generator.train_model()
            st.success("Модель ML обучена!")
        else:
            st.warning("Нет данных для обучения модели. Поиграйте сначала!")

# Игровой цикл
player = st.session_state.player
level = st.session_state.level
physics = st.session_state.physics
player_analyzer = st.session_state.player_analyzer
level_generator = st.session_state.level_generator

# Обработка ввода (кнопки для мобильных устройств)
control_cols = st.columns([1, 2, 1])
with control_cols[0]:
    if st.button("⬅️ Влево", key="mobile_left_btn"):
        player.move_left()
        player_analyzer.log_action("move_left", player, level)
with control_cols[2]:
    if st.button("➡️ Вправо", key="mobile_right_btn"):
        player.move_right()
        player_analyzer.log_action("move_right", player, level)
with control_cols[1]:
    if st.button("⬆️ Прыжок", key="mobile_jump_btn"):
        player.jump()
        player_analyzer.log_action("jump", player, level)

# Обновление физики
physics.apply_gravity(player)
player.y += player.velocity_y
player.x += player.velocity_x

# Проверка столкновений с платформами
player.on_ground = False
for p in level.platforms:
    if physics.check_collision(player, p):
        if player.velocity_y > 0 and player.y + player.height > p.y and player.y < p.y + p.height:
            player.y = p.y - player.height
            player.velocity_y = 0
            player.on_ground = True
        elif player.velocity_y < 0 and player.y < p.y + p.height and player.y + player.height > p.y:
            player.y = p.y + p.height
            player.velocity_y = 0

# Обновление врагов
for enemy in level.enemies:
    if enemy.is_alive():
        enemy.move()
        if enemy.x <= 0 or enemy.x + enemy.width >= 800:
            enemy.reverse_direction()
        for p in level.platforms:
            if physics.check_collision(enemy, p):
                if enemy.velocity_x > 0 and enemy.x + enemy.width > p.x + p.width:
                    enemy.reverse_direction()
                elif enemy.velocity_x < 0 and enemy.x < p.x:
                    enemy.reverse_direction()

        if physics.check_collision(player, enemy):
            player.take_damage(enemy.damage)
            player_analyzer.log_action("take_damage", player, level)
            st.warning(f"Вы получили урон! Здоровье: {player.health}")

# Проверка состояния игрока
if not player.is_alive():
    st.error("Вы погибли! Начните новую игру.")
    st.session_state.deaths += 1
    player_analyzer.log_action("death", player, level)
    reset_level()

# Проверка выхода за границы экрана (падение)
if player.y > 600: # За пределами нижней границы
    st.error("Вы упали! Начните новую игру.")
    st.session_state.deaths += 1
    player_analyzer.log_action("fall_out_of_bounds", player, level)
    reset_level()

# Отображение
with game_container.container():
    st.write(f"Здоровье: {player.health} | Смертей: {st.session_state.deaths}")
    df_actions_for_display = player_analyzer.analyze_data()
    if not df_actions_for_display.empty:
        current_performance = player_analyzer.get_player_performance(df_actions_for_display)
        st.write(f"Текущая сложность уровня: {st.session_state.level_generator.predict_difficulty(current_performance)}")
    else:
        st.write("Текущая сложность уровня: (нет данных для анализа)")

    game_area_html = f"""
    <div style="position: relative; width: 800px; height: 500px; border: 2px solid #333; background-color: #87CEEB; overflow: hidden;">
    """
    if knight_sprite:
        game_area_html += f"<img src=\"data:image/png;base64,{st.image(knight_sprite, use_column_width=False, output_format='PNG')._repr_html_().split('src="')[1].split('"')[0]}\" style=\"position: absolute; left: {player.x}px; top: {player.y}px; width: {player.width}px; height: {player.height}px;\">"
    else:
        game_area_html += f"<div style=\"position: absolute; left: {player.x}px; top: {player.y}px; width: {player.width}px; height: {player.height}px; background-color: blue; border-radius: 5px;\"></div>"

    for p in level.platforms:
        game_area_html += f"<div style=\"position: absolute; left: {p.x}px; top: {p.y}px; width: {p.width}px; height: {p.height}px; background-color: green;\"></div>"
    for e in level.enemies:
        if e.is_alive():
            if goblin_sprite:
                game_area_html += f"<img src=\"data:image/png;base64,{st.image(goblin_sprite, use_column_width=False, output_format='PNG')._repr_html_().split('src="')[1].split('"')[0]}\" style=\"position: absolute; left: {e.x}px; top: {e.y}px; width: {e.width}px; height: {e.height}px;\">"
            else:
                game_area_html += f"<div style=\"position: absolute; left: {e.x}px; top: {e.y}px; width: {e.width}px; height: {e.height}px; background-color: red; border-radius: 50%;\"></div>"
    game_area_html += "</div>"
    st.markdown(game_area_html, unsafe_allow_html=True)

# Задержка для анимации и автоматического обновления
time.sleep(0.05)
st.experimental_rerun()


