class Level:
    def __init__(self, level_data):
        self.platforms = []
        self.enemies = []
        self.collectibles = []
        self.start_x = level_data.get('start_x', 50)
        self.start_y = level_data.get('start_y', 400)
        self.end_x = level_data.get('end_x', 750)

        for p_data in level_data.get('platforms', []):
            self.platforms.append(Platform(p_data['x'], p_data['y'], p_data['width'], p_data['height']))
        for e_data in level_data.get('enemies', []):
            self.enemies.append(Goblin(e_data['x'], e_data['y'], e_data['width'], e_data['height']))

    def draw(self, st_container):
        # В Streamlit мы не можем "рисовать" в традиционном смысле.
        # Вместо этого мы будем использовать HTML/CSS или компоненты Streamlit
        # для отображения элементов. Пока это заглушка.
        pass

class Platform:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height


