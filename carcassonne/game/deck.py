import random
from typing import Optional, List
from .tile import TileDef, TILE_DEFS


class Deck:
    def __init__(self, shuffle: bool = True):
        self.tiles: List[TileDef] = []
        for td in TILE_DEFS:
            if td.tile_type == "start":
                continue
            for _ in range(td.count):
                self.tiles.append(td)
        if shuffle:
            random.shuffle(self.tiles)

    def draw(self) -> Optional[TileDef]:
        if not self.tiles:
            return None
        return self.tiles.pop()

    def remaining(self) -> int:
        return len(self.tiles)

    def peek(self) -> Optional[TileDef]:
        if not self.tiles:
            return None
        return self.tiles[-1]
