from enum import IntEnum
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import copy


class EdgeType(IntEnum):
    FIELD = 0
    ROAD = 1
    CITY = 2


class CenterType(IntEnum):
    NONE = 0
    ROAD = 1
    MONASTERY = 2
    CITY = 3
    CROSSROAD = 4


SIDE_NAMES = ["N", "E", "S", "W"]
OPPOSITE = {"N": "S", "E": "W", "S": "N", "W": "E"}
SIDE_INDEX = {"N": 0, "E": 1, "S": 2, "W": 3}
NEIGHBOR_OFFSET = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}


@dataclass
class TileDef:
    tile_type: str
    edges: List[int]  # [N, E, S, W] as EdgeType values
    internal_connections: List[Tuple[int, int]]  # pairs of side indices connected
    center: int = CenterType.NONE
    shield: bool = False
    count: int = 1


@dataclass
class PlacedTile:
    tile_type: str
    edges: List[int]
    internal_connections: List[Tuple[int, int]]
    center: int
    shield: bool
    rotation: int  # 0, 90, 180, 270
    x: int = 0
    y: int = 0

    def get_edge(self, side: str) -> int:
        idx = SIDE_INDEX[side]
        steps = self.rotation // 90
        original_idx = (idx - steps) % 4
        return self.edges[original_idx]

    def get_rotated_edges(self) -> List[int]:
        steps = self.rotation // 90
        return self.edges[-steps:] + self.edges[:-steps] if steps else list(self.edges)

    def get_rotated_connections(self) -> List[Tuple[int, int]]:
        steps = self.rotation // 90
        return [((a + steps) % 4, (b + steps) % 4) for a, b in self.internal_connections]


TILE_DEFS: List[TileDef] = [
    # Straight road (N-S)
    TileDef("straight_road", [1, 0, 1, 0], [(0, 2)], CenterType.ROAD, count=8),
    # Curve road (N-W)
    TileDef("curve_road", [1, 0, 0, 1], [(0, 3)], CenterType.ROAD, count=9),
    # T-crossroad (N, E, W — no S)
    TileDef("t_crossroad", [1, 1, 0, 1], [], CenterType.CROSSROAD, count=4),
    # Full crossroad
    TileDef("x_crossroad", [1, 1, 1, 1], [], CenterType.CROSSROAD, count=1),
    # City edge (N is city)
    TileDef("city_edge", [2, 0, 0, 0], [], CenterType.NONE, count=5),
    # City edge with road (N city, E-W road)
    TileDef("city_edge_road", [2, 0, 1, 1], [(2, 3)], CenterType.ROAD, count=4), # road S-W? let's do road curve under city
    # City wall (N city, with road E-S)
    TileDef("city_edge_road_right", [2, 1, 1, 0], [(1, 2)], CenterType.ROAD, count=3),
    # City two edges adjacent (N, E)
    TileDef("city_two_adj", [2, 2, 0, 0], [(0, 1)], CenterType.CITY, count=3),
    # City two edges adjacent with shield
    TileDef("city_two_adj_shield", [2, 2, 0, 0], [(0, 1)], CenterType.CITY, True, count=2),
    # City two edges opposite (N, S) — not connected
    TileDef("city_two_opp", [2, 0, 2, 0], [], CenterType.NONE, count=3),
    # City three edges (N, E, W)
    TileDef("city_three", [2, 2, 0, 2], [(0, 1), (0, 3), (1, 3)], CenterType.CITY, count=3),
    # City three edges with shield
    TileDef("city_three_shield", [2, 2, 0, 2], [(0, 1), (0, 3), (1, 3)], CenterType.CITY, True, count=1),
    # City three with road
    TileDef("city_three_road", [2, 2, 1, 2], [(0, 1), (0, 3), (1, 3)], CenterType.CITY, count=2),
    # Full city (all 4 sides)
    TileDef("city_full", [2, 2, 2, 2], [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)], CenterType.CITY, True, count=1),
    # Monastery
    TileDef("monastery", [0, 0, 0, 0], [], CenterType.MONASTERY, count=4),
    # Monastery with road (road going S)
    TileDef("monastery_road", [0, 0, 1, 0], [], CenterType.MONASTERY, count=2),
    # Start tile: city N, road E-W
    TileDef("start", [2, 1, 0, 1], [(1, 3)], CenterType.ROAD, count=1),
]


def create_placed_tile(tile_def: TileDef, rotation: int = 0, x: int = 0, y: int = 0) -> PlacedTile:
    return PlacedTile(
        tile_type=tile_def.tile_type,
        edges=list(tile_def.edges),
        internal_connections=list(tile_def.internal_connections),
        center=tile_def.center,
        shield=tile_def.shield,
        rotation=rotation,
        x=x,
        y=y,
    )
