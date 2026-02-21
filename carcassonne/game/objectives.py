import random
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class Objective:
    obj_id: str
    name: str
    description: str
    category: str  # territory, building, strategy
    check_fn_name: str
    bonus_points: int
    icon: str


OBJECTIVES = [
    Objective("road_king", "Road King", "Control the longest completed road (5+ tiles)",
              "building", "check_longest_road", 10, "🛤️"),
    Objective("city_lord", "City Lord", "Control the largest completed city (4+ tiles)",
              "building", "check_largest_city", 12, "🏰"),
    Objective("monk_master", "Monk Master", "Complete 2 or more monasteries",
              "building", "check_monasteries", 8, "⛪"),
    Objective("field_baron", "Field Baron", "Have meeples adjacent to 3+ completed cities at end",
              "territory", "check_field_baron", 10, "🌾"),
    Objective("expansionist", "Expansionist", "Place tiles in all 4 quadrants of the board",
              "territory", "check_quadrants", 6, "🧭"),
    Objective("meeple_hoarder", "Meeple Hoarder", "End the game with 5+ meeples in hand",
              "strategy", "check_meeple_hoard", 8, "👥"),
    Objective("aggressive", "Conqueror", "Score points from 2+ features shared with opponents",
              "strategy", "check_shared_scoring", 10, "⚔️"),
    Objective("diverse", "Renaissance", "Score from at least 3 different feature types",
              "strategy", "check_diversity", 7, "🎨"),
    Objective("late_bloomer", "Late Bloomer", "Score 15+ points in the last 10 turns",
              "strategy", "check_late_scoring", 9, "🌸"),
    Objective("blocker", "Wall Builder", "Place 5+ tiles adjacent to opponent meeples without claiming",
              "strategy", "check_blocking", 8, "🧱"),
]


class ObjectiveManager:
    def __init__(self):
        self.player_objectives: Dict[str, List[Objective]] = {}
        self.completed: Dict[str, List[str]] = {}  # player_id -> [obj_id]

    def deal_objectives(self, player_ids: List[str], count: int = 2):
        available = list(OBJECTIVES)
        random.shuffle(available)
        for pid in player_ids:
            self.player_objectives[pid] = available[:count]
            available = available[count:]
            self.completed[pid] = []

    def evaluate_all(self, game) -> Dict[str, List[dict]]:
        results = {}
        for pid, objectives in self.player_objectives.items():
            player_results = []
            for obj in objectives:
                checker = ObjectiveChecker(game, pid)
                met = getattr(checker, obj.check_fn_name, lambda: False)()
                if met and obj.obj_id not in self.completed.get(pid, []):
                    self.completed[pid].append(obj.obj_id)
                player_results.append({
                    "obj_id": obj.obj_id,
                    "name": obj.name,
                    "description": obj.description,
                    "icon": obj.icon,
                    "bonus_points": obj.bonus_points,
                    "completed": obj.obj_id in self.completed.get(pid, []),
                })
            results[pid] = player_results
        return results

    def get_bonus_points(self) -> Dict[str, int]:
        bonuses = {}
        for pid, objectives in self.player_objectives.items():
            total = 0
            for obj in objectives:
                if obj.obj_id in self.completed.get(pid, []):
                    total += obj.bonus_points
            bonuses[pid] = total
        return bonuses

    def to_dict(self, for_player: Optional[str] = None) -> dict:
        data = {}
        for pid, objectives in self.player_objectives.items():
            if for_player and pid != for_player:
                data[pid] = {"count": len(objectives), "objectives": None}
            else:
                data[pid] = {
                    "count": len(objectives),
                    "objectives": [
                        {
                            "obj_id": o.obj_id, "name": o.name,
                            "description": o.description, "icon": o.icon,
                            "bonus_points": o.bonus_points, "category": o.category,
                            "completed": o.obj_id in self.completed.get(pid, []),
                        }
                        for o in objectives
                    ],
                }
        return data


class ObjectiveChecker:
    def __init__(self, game, player_id: str):
        self.game = game
        self.pid = player_id
        self.board = game.board
        self.meeples = game.meeples
        self.scoring = game.scoring
        self.history = game.history

    def check_longest_road(self) -> bool:
        from .tile import EdgeType
        road_features = self.board.get_features(EdgeType.ROAD)
        max_len = 0
        for f in road_features:
            if self.board.is_feature_complete(f, EdgeType.ROAD):
                on_f = self.meeples.get_meeples_on_feature(f)
                my_count = sum(1 for m in on_f if m.player_id == self.pid)
                if my_count > 0:
                    tiles = set((n[0], n[1]) for n in f)
                    max_len = max(max_len, len(tiles))
        return max_len >= 5

    def check_largest_city(self) -> bool:
        from .tile import EdgeType
        city_features = self.board.get_features(EdgeType.CITY)
        max_size = 0
        for f in city_features:
            if self.board.is_feature_complete(f, EdgeType.CITY):
                on_f = self.meeples.get_meeples_on_feature(f)
                my_count = sum(1 for m in on_f if m.player_id == self.pid)
                if my_count > 0:
                    tiles = set((n[0], n[1]) for n in f)
                    max_size = max(max_size, len(tiles))
        return max_size >= 4

    def check_monasteries(self) -> bool:
        completed_count = 0
        for ev in self.game.score_events:
            if (ev.get("player_id") == self.pid
                    and ev.get("reason") == "completed_monastery"):
                completed_count += 1
        return completed_count >= 2

    def check_field_baron(self) -> bool:
        from .tile import EdgeType
        my_field_meeples = [
            m for m in self.meeples.get_player_meeples(self.pid)
            if m.position in ("N", "E", "S", "W")
            and self.board.feature_graph.nodes.get(m.node_id, {}).get("edge_type") == EdgeType.FIELD
        ]
        if not my_field_meeples:
            return False
        completed_cities = []
        for f in self.board.get_features(EdgeType.CITY):
            if self.board.is_feature_complete(f, EdgeType.CITY):
                completed_cities.append(set((n[0], n[1]) for n in f))

        adjacent_count = 0
        for ct in completed_cities:
            for m in my_field_meeples:
                for cx, cy in ct:
                    if abs(m.x - cx) <= 1 and abs(m.y - cy) <= 1:
                        adjacent_count += 1
                        break
                else:
                    continue
                break
        return adjacent_count >= 3

    def check_quadrants(self) -> bool:
        my_moves = [m for m in self.history if m["player_id"] == self.pid]
        quadrants = set()
        for m in my_moves:
            x, y = m["x"], m["y"]
            q = (1 if x >= 0 else -1, 1 if y >= 0 else -1)
            quadrants.add(q)
        return len(quadrants) >= 4

    def check_meeple_hoard(self) -> bool:
        return self.meeples.available(self.pid) >= 5

    def check_shared_scoring(self) -> bool:
        shared_count = 0
        for ev in self.game.score_events:
            if ev.get("player_id") != self.pid:
                continue
            reason = ev.get("reason", "")
            if reason.startswith("completed_"):
                feat_type_str = ev.get("feature_type", "")
                from .tile import EdgeType
                ft = EdgeType.CITY if feat_type_str == "city" else EdgeType.ROAD if feat_type_str == "road" else None
                if ft is not None:
                    tile_list = ev.get("tiles", [])
                    for other_ev in self.game.score_events:
                        if (other_ev.get("player_id") != self.pid
                                and other_ev.get("reason") == reason
                                and other_ev.get("tiles") == tile_list):
                            shared_count += 1
                            break
        return shared_count >= 2

    def check_diversity(self) -> bool:
        types_scored = set()
        for ev in self.game.score_events:
            if ev.get("player_id") == self.pid and ev.get("points", 0) > 0:
                types_scored.add(ev.get("feature_type", ""))
        return len(types_scored) >= 3

    def check_late_scoring(self) -> bool:
        total_turns = len(self.history)
        cutoff = max(0, total_turns - 10)
        late_points = 0
        for ev in self.game.score_events:
            if ev.get("player_id") == self.pid and ev.get("turn", 0) >= cutoff:
                late_points += ev.get("points", 0)
        return late_points >= 15

    def check_blocking(self) -> bool:
        block_count = 0
        my_moves = [m for m in self.history if m["player_id"] == self.pid]
        for move in my_moves:
            x, y = move["x"], move["y"]
            from .tile import SIDE_NAMES, NEIGHBOR_OFFSET
            for side in SIDE_NAMES:
                dx, dy = NEIGHBOR_OFFSET[side]
                nx, ny = x + dx, y + dy
                opp_at = [m for m in self.meeples.placed
                          if m.x == nx and m.y == ny and m.player_id != self.pid]
                if opp_at:
                    my_at = [m for m in self.meeples.placed
                             if m.x == x and m.y == y and m.player_id == self.pid]
                    if not my_at:
                        block_count += 1
                        break
        return block_count >= 5
