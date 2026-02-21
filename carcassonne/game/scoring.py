from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from .tile import EdgeType, CenterType, SIDE_NAMES, NEIGHBOR_OFFSET, OPPOSITE


@dataclass
class Meeple:
    player_id: str
    x: int
    y: int
    position: str  # side name ("N","E","S","W") or "CENTER" for monastery, "FIELD_X" for fields
    meeple_type: str = "normal"  # normal, big (future)

    @property
    def coord(self) -> Tuple[int, int]:
        return (self.x, self.y)

    @property
    def node_id(self) -> Tuple:
        return (self.x, self.y, self.position)


MEEPLES_PER_PLAYER = 7


class MeepleManager:
    def __init__(self):
        self.placed: List[Meeple] = []
        self.meeple_counts: Dict[str, int] = {}

    def init_player(self, player_id: str):
        self.meeple_counts[player_id] = MEEPLES_PER_PLAYER

    def available(self, player_id: str) -> int:
        return self.meeple_counts.get(player_id, 0)

    def place(self, meeple: Meeple) -> bool:
        if self.available(meeple.player_id) <= 0:
            return False
        self.placed.append(meeple)
        self.meeple_counts[meeple.player_id] -= 1
        return True

    def return_meeples(self, meeples: List[Meeple]):
        for m in meeples:
            self.placed.remove(m)
            self.meeple_counts[m.player_id] += 1

    def get_meeples_on_feature(self, feature_nodes: Set[Tuple]) -> List[Meeple]:
        return [m for m in self.placed if m.node_id in feature_nodes]

    def get_meeples_at(self, x: int, y: int) -> List[Meeple]:
        return [m for m in self.placed if m.x == x and m.y == y]

    def get_player_meeples(self, player_id: str) -> List[Meeple]:
        return [m for m in self.placed if m.player_id == player_id]

    def to_dict(self) -> dict:
        return {
            "placed": [
                {"player_id": m.player_id, "x": m.x, "y": m.y,
                 "position": m.position, "type": m.meeple_type}
                for m in self.placed
            ],
            "counts": dict(self.meeple_counts),
        }


@dataclass
class ScoreEvent:
    player_id: str
    points: int
    reason: str
    feature_type: str
    tiles: List[Tuple[int, int]]
    turn: int = 0


class ScoringEngine:
    def __init__(self, board, meeple_mgr: MeepleManager):
        self.board = board
        self.meeples = meeple_mgr
        self.score_log: List[ScoreEvent] = []

    def check_and_score_completed(self, turn: int) -> List[ScoreEvent]:
        events = []
        events.extend(self._score_completed_roads(turn))
        events.extend(self._score_completed_cities(turn))
        events.extend(self._score_completed_monasteries(turn))
        return events

    def _score_completed_roads(self, turn: int) -> List[ScoreEvent]:
        events = []
        road_features = self.board.get_features(EdgeType.ROAD)

        for feature in road_features:
            if not self.board.is_feature_complete(feature, EdgeType.ROAD):
                continue

            meeples = self.meeples.get_meeples_on_feature(feature)
            if not meeples:
                continue

            tile_coords = set((n[0], n[1]) for n in feature)
            points = len(tile_coords)

            winners = self._get_majority_owners(meeples)
            for pid in winners:
                event = ScoreEvent(pid, points, "completed_road", "road",
                                   list(tile_coords), turn)
                events.append(event)
                self.score_log.append(event)

            self.meeples.return_meeples(meeples)

        return events

    def _score_completed_cities(self, turn: int) -> List[ScoreEvent]:
        events = []
        city_features = self.board.get_features(EdgeType.CITY)

        for feature in city_features:
            if not self.board.is_feature_complete(feature, EdgeType.CITY):
                continue

            meeples = self.meeples.get_meeples_on_feature(feature)
            if not meeples:
                continue

            tile_coords = set((n[0], n[1]) for n in feature)
            points = len(tile_coords) * 2

            shield_count = sum(
                1 for coord in tile_coords
                if coord in self.board.grid and self.board.grid[coord].shield
            )
            points += shield_count * 2

            winners = self._get_majority_owners(meeples)
            for pid in winners:
                event = ScoreEvent(pid, points, "completed_city", "city",
                                   list(tile_coords), turn)
                events.append(event)
                self.score_log.append(event)

            self.meeples.return_meeples(meeples)

        return events

    def _score_completed_monasteries(self, turn: int) -> List[ScoreEvent]:
        events = []

        monastery_meeples = [m for m in self.meeples.placed if m.position == "CENTER"]
        for m in monastery_meeples:
            if self._is_monastery_complete(m.x, m.y):
                points = 9
                event = ScoreEvent(m.player_id, points, "completed_monastery",
                                   "monastery", [(m.x, m.y)], turn)
                events.append(event)
                self.score_log.append(event)
                self.meeples.return_meeples([m])

        return events

    def _is_monastery_complete(self, x: int, y: int) -> bool:
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if (x + dx, y + dy) not in self.board.grid:
                    return False
        return True

    def score_end_game(self, turn: int) -> List[ScoreEvent]:
        events = []
        events.extend(self._score_incomplete_roads(turn))
        events.extend(self._score_incomplete_cities(turn))
        events.extend(self._score_incomplete_monasteries(turn))
        events.extend(self._score_fields(turn))
        return events

    def _score_incomplete_roads(self, turn: int) -> List[ScoreEvent]:
        events = []
        road_features = self.board.get_features(EdgeType.ROAD)

        for feature in road_features:
            if self.board.is_feature_complete(feature, EdgeType.ROAD):
                continue
            meeples = self.meeples.get_meeples_on_feature(feature)
            if not meeples:
                continue

            tile_coords = set((n[0], n[1]) for n in feature)
            points = len(tile_coords)

            winners = self._get_majority_owners(meeples)
            for pid in winners:
                event = ScoreEvent(pid, points, "incomplete_road", "road",
                                   list(tile_coords), turn)
                events.append(event)
                self.score_log.append(event)

            self.meeples.return_meeples(meeples)

        return events

    def _score_incomplete_cities(self, turn: int) -> List[ScoreEvent]:
        events = []
        city_features = self.board.get_features(EdgeType.CITY)

        for feature in city_features:
            if self.board.is_feature_complete(feature, EdgeType.CITY):
                continue
            meeples = self.meeples.get_meeples_on_feature(feature)
            if not meeples:
                continue

            tile_coords = set((n[0], n[1]) for n in feature)
            points = len(tile_coords)
            shield_count = sum(
                1 for coord in tile_coords
                if coord in self.board.grid and self.board.grid[coord].shield
            )
            points += shield_count

            winners = self._get_majority_owners(meeples)
            for pid in winners:
                event = ScoreEvent(pid, points, "incomplete_city", "city",
                                   list(tile_coords), turn)
                events.append(event)
                self.score_log.append(event)

            self.meeples.return_meeples(meeples)

        return events

    def _score_incomplete_monasteries(self, turn: int) -> List[ScoreEvent]:
        events = []
        monastery_meeples = [m for m in self.meeples.placed if m.position == "CENTER"]

        for m in list(monastery_meeples):
            count = 0
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if (m.x + dx, m.y + dy) in self.board.grid:
                        count += 1
            event = ScoreEvent(m.player_id, count, "incomplete_monastery",
                               "monastery", [(m.x, m.y)], turn)
            events.append(event)
            self.score_log.append(event)
            self.meeples.return_meeples([m])

        return events

    def _score_fields(self, turn: int) -> List[ScoreEvent]:
        events = []
        field_features = self.board.get_features(EdgeType.FIELD)

        completed_cities = set()
        city_features = self.board.get_features(EdgeType.CITY)
        for cf in city_features:
            if self.board.is_feature_complete(cf, EdgeType.CITY):
                completed_cities.add(frozenset(cf))

        for feature in field_features:
            meeples = self.meeples.get_meeples_on_feature(feature)
            if not meeples:
                continue

            field_tiles = set((n[0], n[1]) for n in feature)
            adjacent_completed = 0

            for city_set in completed_cities:
                city_tiles = set((n[0], n[1]) for n in city_set)
                if self._field_touches_city(field_tiles, city_tiles):
                    adjacent_completed += 1

            if adjacent_completed == 0:
                self.meeples.return_meeples(meeples)
                continue

            points = adjacent_completed * 3

            winners = self._get_majority_owners(meeples)
            for pid in winners:
                event = ScoreEvent(pid, points, "field", "field",
                                   list(field_tiles), turn)
                events.append(event)
                self.score_log.append(event)

            self.meeples.return_meeples(meeples)

        return events

    def _field_touches_city(self, field_tiles: Set[Tuple], city_tiles: Set[Tuple]) -> bool:
        for ft in field_tiles:
            for ct in city_tiles:
                dx = abs(ft[0] - ct[0])
                dy = abs(ft[1] - ct[1])
                if dx <= 1 and dy <= 1:
                    return True
        return False

    def _get_majority_owners(self, meeples: List) -> List[str]:
        counts: Dict[str, int] = {}
        for m in meeples:
            counts[m.player_id] = counts.get(m.player_id, 0) + 1
        if not counts:
            return []
        max_count = max(counts.values())
        return [pid for pid, c in counts.items() if c == max_count]
