from typing import Dict, List, Optional, Tuple, Set
from .board import Board
from .tile import (
    PlacedTile, TileDef, EdgeType, CenterType,
    SIDE_NAMES, SIDE_INDEX, OPPOSITE, NEIGHBOR_OFFSET,
    create_placed_tile,
)
import copy
import networkx as nx


class EngineerManager:
    def __init__(self):
        self.available: Dict[str, bool] = {}  # pid -> has engineer
        self.used_this_game: Dict[str, int] = {}  # pid -> times used

    def init_player(self, player_id: str):
        self.available[player_id] = True
        self.used_this_game[player_id] = 0

    def has_engineer(self, player_id: str) -> bool:
        return self.available.get(player_id, False)

    def use_engineer(self, player_id: str) -> bool:
        if not self.available.get(player_id, False):
            return False
        self.available[player_id] = False
        self.used_this_game[player_id] = self.used_this_game.get(player_id, 0) + 1
        return True

    def return_engineer(self, player_id: str):
        self.available[player_id] = True

    def to_dict(self) -> dict:
        return {
            "available": dict(self.available),
            "used": dict(self.used_this_game),
        }


def get_valid_engineer_targets(board: Board, meeple_placed: list,
                               player_id: str) -> List[dict]:
    targets = []
    for (x, y), tile in board.grid.items():
        if x == 0 and y == 0:
            continue

        has_own_meeple = any(m.x == x and m.y == y and m.player_id == player_id
                            for m in meeple_placed)
        has_opponent_meeple = any(m.x == x and m.y == y and m.player_id != player_id
                                 for m in meeple_placed)
        if has_opponent_meeple:
            continue

        current_rot = tile.rotation
        new_rot = (current_rot + 90) % 360

        if _is_rotation_legal(board, x, y, tile, new_rot, meeple_placed):
            targets.append({
                "x": x, "y": y,
                "tile_type": tile.tile_type,
                "current_rotation": current_rot,
                "new_rotation": new_rot,
            })

    return targets


def _is_rotation_legal(board: Board, x: int, y: int, tile: PlacedTile,
                       new_rotation: int, meeple_placed: list) -> bool:
    temp_tile = PlacedTile(
        tile_type=tile.tile_type,
        edges=list(tile.edges),
        internal_connections=list(tile.internal_connections),
        center=tile.center,
        shield=tile.shield,
        rotation=new_rotation,
        x=x, y=y,
    )
    new_edges = temp_tile.get_rotated_edges()

    for i, side in enumerate(SIDE_NAMES):
        dx, dy = NEIGHBOR_OFFSET[side]
        nx_, ny_ = x + dx, y + dy
        if (nx_, ny_) in board.grid:
            neighbor = board.grid[(nx_, ny_)]
            opp = OPPOSITE[side]
            neighbor_edge = neighbor.get_edge(opp)
            if new_edges[i] != neighbor_edge:
                return False

    meeples_on_tile = [m for m in meeple_placed if m.x == x and m.y == y]
    if meeples_on_tile:
        old_edges = tile.get_rotated_edges()
        for m in meeples_on_tile:
            if m.position in SIDE_NAMES:
                si = SIDE_INDEX[m.position]
                if old_edges[si] != new_edges[si]:
                    return False

    return True


def apply_engineer_rotation(board: Board, x: int, y: int) -> bool:
    if (x, y) not in board.grid:
        return False

    tile = board.grid[(x, y)]
    new_rotation = (tile.rotation + 90) % 360

    for i, side in enumerate(SIDE_NAMES):
        node = (x, y, side)
        neighbors_to_remove = list(board.feature_graph.neighbors(node))
        for nb in neighbors_to_remove:
            board.feature_graph.remove_edge(node, nb)
        board.feature_graph.remove_node(node)

    center_node = (x, y, "CENTER")
    if center_node in board.feature_graph:
        board.feature_graph.remove_node(center_node)

    tile.rotation = new_rotation
    board._add_to_graph(tile)

    return True
