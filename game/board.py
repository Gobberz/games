from typing import Dict, Tuple, List, Optional, Set
import networkx as nx
from .tile import (
    PlacedTile, TileDef, TILE_DEFS, EdgeType, CenterType,
    SIDE_NAMES, SIDE_INDEX, OPPOSITE, NEIGHBOR_OFFSET,
    create_placed_tile,
)
import random
import copy


Coord = Tuple[int, int]


class Board:
    def __init__(self):
        self.grid: Dict[Coord, PlacedTile] = {}
        self.feature_graph = nx.Graph()
        self.open_slots: Set[Coord] = set()
        self._place_start_tile()

    def _place_start_tile(self):
        start_def = next(d for d in TILE_DEFS if d.tile_type == "start")
        tile = create_placed_tile(start_def, rotation=0, x=0, y=0)
        self.grid[(0, 0)] = tile
        self._add_to_graph(tile)
        self._update_open_slots((0, 0))

    def _add_to_graph(self, tile: PlacedTile):
        x, y = tile.x, tile.y
        rotated_edges = tile.get_rotated_edges()
        rotated_conns = tile.get_rotated_connections()

        for i, side in enumerate(SIDE_NAMES):
            node_id = (x, y, side)
            self.feature_graph.add_node(node_id, edge_type=rotated_edges[i])

        for a, b in rotated_conns:
            side_a = SIDE_NAMES[a]
            side_b = SIDE_NAMES[b]
            node_a = (x, y, side_a)
            node_b = (x, y, side_b)
            self.feature_graph.add_edge(node_a, node_b, kind="internal")

        if tile.center == CenterType.MONASTERY:
            monastery_node = (x, y, "CENTER")
            self.feature_graph.add_node(monastery_node, edge_type=-1, is_monastery=True)

        for side in SIDE_NAMES:
            dx, dy = NEIGHBOR_OFFSET[side]
            nx_, ny_ = x + dx, y + dy
            if (nx_, ny_) in self.grid:
                opp = OPPOSITE[side]
                node_here = (x, y, side)
                node_there = (nx_, ny_, opp)
                self.feature_graph.add_edge(node_here, node_there, kind="external")

    def _update_open_slots(self, coord: Coord):
        x, y = coord
        self.open_slots.discard(coord)
        for side in SIDE_NAMES:
            dx, dy = NEIGHBOR_OFFSET[side]
            neighbor = (x + dx, y + dy)
            if neighbor not in self.grid:
                self.open_slots.add(neighbor)

    def get_valid_placements(self, tile_def: TileDef) -> List[Tuple[Coord, int]]:
        valid = []
        for coord in self.open_slots:
            for rotation in [0, 90, 180, 270]:
                if self._is_placement_valid(tile_def, coord, rotation):
                    valid.append((coord, rotation))
        return valid

    def _is_placement_valid(self, tile_def: TileDef, coord: Coord, rotation: int) -> bool:
        x, y = coord
        temp = create_placed_tile(tile_def, rotation, x, y)
        rotated_edges = temp.get_rotated_edges()
        has_neighbor = False

        for i, side in enumerate(SIDE_NAMES):
            dx, dy = NEIGHBOR_OFFSET[side]
            neighbor_coord = (x + dx, y + dy)
            if neighbor_coord in self.grid:
                has_neighbor = True
                neighbor = self.grid[neighbor_coord]
                opp = OPPOSITE[side]
                neighbor_edge = neighbor.get_edge(opp)
                if rotated_edges[i] != neighbor_edge:
                    return False

        return has_neighbor

    def place_tile(self, tile_def: TileDef, coord: Coord, rotation: int) -> Optional[PlacedTile]:
        if coord in self.grid:
            return None
        if not self._is_placement_valid(tile_def, coord, rotation):
            return None

        tile = create_placed_tile(tile_def, rotation, coord[0], coord[1])
        self.grid[coord] = tile
        self._add_to_graph(tile)
        self._update_open_slots(coord)
        return tile

    def get_features(self, feature_type: int) -> List[Set[Tuple]]:
        subgraph_nodes = [
            n for n in self.feature_graph.nodes
            if len(n) == 3 and n[2] != "CENTER"
            and self.feature_graph.nodes[n].get("edge_type") == feature_type
        ]
        subgraph = self.feature_graph.subgraph(subgraph_nodes)
        return [set(c) for c in nx.connected_components(subgraph)]

    def is_feature_complete(self, feature_nodes: Set[Tuple], feature_type: int) -> bool:
        if feature_type == EdgeType.ROAD:
            return self._is_road_complete(feature_nodes)
        elif feature_type == EdgeType.CITY:
            return self._is_city_complete(feature_nodes)
        return False

    def _is_road_complete(self, nodes: Set[Tuple]) -> bool:
        for node in nodes:
            x, y, side = node
            dx, dy = NEIGHBOR_OFFSET[side]
            neighbor_coord = (x + dx, y + dy)
            opp = OPPOSITE[side]
            neighbor_node = (neighbor_coord[0], neighbor_coord[1], opp)

            has_internal = any(
                (x, y, s) in nodes and self.feature_graph.has_edge(node, (x, y, s))
                for s in SIDE_NAMES if s != side
            )
            has_external = neighbor_node in nodes

            if not has_internal and not has_external:
                tile = self.grid.get((x, y))
                if tile and tile.center in (CenterType.CROSSROAD,):
                    continue
                return False

        return True

    def _is_city_complete(self, nodes: Set[Tuple]) -> bool:
        for node in nodes:
            x, y, side = node
            dx, dy = NEIGHBOR_OFFSET[side]
            neighbor_coord = (x + dx, y + dy)
            opp = OPPOSITE[side]
            neighbor_node = (neighbor_coord[0], neighbor_coord[1], opp)

            if neighbor_node not in nodes:
                return False

        return True

    def to_dict(self) -> dict:
        tiles = {}
        for (x, y), tile in self.grid.items():
            tiles[f"{x},{y}"] = {
                "tile_type": tile.tile_type,
                "edges": tile.get_rotated_edges(),
                "rotation": tile.rotation,
                "x": x,
                "y": y,
                "center": tile.center,
                "shield": tile.shield,
            }
        return {
            "tiles": tiles,
            "open_slots": [list(s) for s in self.open_slots],
        }

    def get_feature_containing(self, node: Tuple) -> Optional[Set[Tuple]]:
        if node not in self.feature_graph:
            return None
        edge_type = self.feature_graph.nodes[node].get("edge_type")
        if edge_type is None:
            return None
        features = self.get_features(edge_type)
        for f in features:
            if node in f:
                return f
        return None

    def get_valid_meeple_positions(self, x: int, y: int, placed_meeple_nodes: set) -> List[dict]:
        tile = self.grid.get((x, y))
        if not tile:
            return []

        rotated_edges = tile.get_rotated_edges()
        positions = []
        seen_features = set()

        for i, side in enumerate(SIDE_NAMES):
            node = (x, y, side)
            feature = self.get_feature_containing(node)
            if feature is None:
                continue

            feature_key = frozenset(feature)
            if feature_key in seen_features:
                continue
            seen_features.add(feature_key)

            if feature_key & placed_meeple_nodes:
                continue

            positions.append({
                "position": side,
                "feature_type": rotated_edges[i],
                "feature_size": len(set((n[0], n[1]) for n in feature)),
            })

        if tile.center == CenterType.MONASTERY:
            positions.append({
                "position": "CENTER",
                "feature_type": -1,
                "feature_size": 1,
            })

        return positions
