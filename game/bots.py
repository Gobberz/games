import random
import copy
import math
from typing import List, Optional, Tuple, Dict
from .board import Board
from .tile import TileDef, EdgeType, CenterType, SIDE_NAMES, NEIGHBOR_OFFSET, create_placed_tile
from .scoring import MeepleManager, Meeple, ScoringEngine, MEEPLES_PER_PLAYER


class BotMove:
    def __init__(self, tile_idx: int, x: int, y: int, rotation: int,
                 meeple_position: Optional[str] = None, score: float = 0.0):
        self.tile_idx = tile_idx
        self.x = x
        self.y = y
        self.rotation = rotation
        self.meeple_position = meeple_position
        self.score = score

    def to_dict(self):
        return {
            "tile_idx": self.tile_idx,
            "x": self.x, "y": self.y,
            "rotation": self.rotation,
            "meeple_position": self.meeple_position,
            "score": self.score,
        }


class RandomBot:
    def choose_move(self, game_state) -> Optional[BotMove]:
        board = game_state["board"]
        hand = game_state["hand"]
        player_id = game_state["player_id"]
        meeples_available = game_state["meeples_available"]
        placed_meeple_nodes = game_state["placed_meeple_nodes"]

        all_moves = []
        for i, tile_def in enumerate(hand):
            placements = board.get_valid_placements(tile_def)
            for coord, rot in placements:
                all_moves.append((i, coord[0], coord[1], rot, tile_def))

        if not all_moves:
            return None

        idx, x, y, rot, tile_def = random.choice(all_moves)

        meeple_pos = None
        if meeples_available > 0 and random.random() < 0.4:
            temp_board = self._simulate_place(board, tile_def, x, y, rot)
            if temp_board:
                positions = temp_board.get_valid_meeple_positions(x, y, placed_meeple_nodes)
                if positions:
                    meeple_pos = random.choice(positions)["position"]

        return BotMove(idx, x, y, rot, meeple_pos)

    def _simulate_place(self, board, tile_def, x, y, rot):
        temp = copy.deepcopy(board)
        result = temp.place_tile(tile_def, (x, y), rot)
        return temp if result else None


class MinimaxBot:
    def __init__(self, max_depth: int = 2, max_moves_sample: int = 15):
        self.max_depth = max_depth
        self.max_moves_sample = max_moves_sample

    def choose_move(self, game_state) -> Optional[BotMove]:
        board = game_state["board"]
        hand = game_state["hand"]
        player_id = game_state["player_id"]
        opponent_id = game_state["opponent_id"]
        meeples_available = game_state["meeples_available"]
        placed_meeple_nodes = game_state["placed_meeple_nodes"]
        meeple_mgr = game_state["meeple_mgr"]
        scores = game_state["scores"]

        all_moves = []
        for i, tile_def in enumerate(hand):
            placements = board.get_valid_placements(tile_def)
            for coord, rot in placements:
                all_moves.append((i, coord[0], coord[1], rot, tile_def))

        if not all_moves:
            return None

        best_move = None
        best_score = -math.inf

        sample = all_moves
        if len(sample) > self.max_moves_sample:
            sample = random.sample(all_moves, self.max_moves_sample)

        for idx, x, y, rot, tile_def in sample:
            meeple_options = self._get_meeple_options(
                board, tile_def, x, y, rot, placed_meeple_nodes
            )
            options_to_try = [None] + meeple_options if meeples_available > 0 else [None]

            for mpos in options_to_try:
                score = self._evaluate_move(
                    board, tile_def, x, y, rot, mpos,
                    player_id, opponent_id, meeple_mgr, scores
                )
                if score > best_score:
                    best_score = score
                    best_move = BotMove(idx, x, y, rot, mpos, score)

        return best_move

    def _get_meeple_options(self, board, tile_def, x, y, rot, placed_nodes):
        temp = copy.deepcopy(board)
        result = temp.place_tile(tile_def, (x, y), rot)
        if not result:
            return []
        positions = temp.get_valid_meeple_positions(x, y, placed_nodes)
        return [p["position"] for p in positions]

    def _evaluate_move(self, board, tile_def, x, y, rot, meeple_pos,
                       player_id, opponent_id, meeple_mgr, scores):
        temp_board = copy.deepcopy(board)
        temp_meeples = copy.deepcopy(meeple_mgr)

        result = temp_board.place_tile(tile_def, (x, y), rot)
        if not result:
            return -math.inf

        if meeple_pos:
            m = Meeple(player_id, x, y, meeple_pos)
            temp_meeples.place(m)

        temp_scoring = ScoringEngine(temp_board, temp_meeples)
        events = temp_scoring.check_and_score_completed(0)

        my_immediate = sum(e.points for e in events if e.player_id == player_id)
        opp_immediate = sum(e.points for e in events if e.player_id == opponent_id)

        potential = self._evaluate_potential(
            temp_board, temp_meeples, player_id, opponent_id
        )

        city_bonus = self._city_control_bonus(temp_board, temp_meeples, player_id, x, y)
        aggression = self._aggression_score(temp_board, temp_meeples, opponent_id, x, y)
        position_value = self._position_value(temp_board, x, y)

        score = (
            my_immediate * 3.0
            - opp_immediate * 2.0
            + potential * 1.0
            + city_bonus * 1.5
            + aggression * 0.8
            + position_value * 0.3
        )

        if meeple_pos:
            meeples_left = temp_meeples.available(player_id)
            if meeples_left <= 1:
                score -= 3.0
            elif meeples_left <= 2:
                score -= 1.0

        return score

    def _evaluate_potential(self, board, meeples, player_id, opponent_id):
        score = 0.0

        for feat_type in [EdgeType.ROAD, EdgeType.CITY]:
            features = board.get_features(feat_type)
            for feature in features:
                on_feature = meeples.get_meeples_on_feature(feature)
                if not on_feature:
                    continue

                tile_coords = set((n[0], n[1]) for n in feature)
                size = len(tile_coords)

                my_count = sum(1 for m in on_feature if m.player_id == player_id)
                opp_count = len(on_feature) - my_count

                if my_count > opp_count:
                    multiplier = 2.0 if feat_type == EdgeType.CITY else 1.0
                    completeness = self._feature_completeness(board, feature, feat_type)
                    score += size * multiplier * completeness
                elif opp_count > my_count:
                    score -= size * 0.5

        return score

    def _feature_completeness(self, board, feature, feat_type):
        if feat_type == EdgeType.CITY:
            total_edges = len(feature)
            open_edges = 0
            for node in feature:
                x, y, side = node
                dx, dy = NEIGHBOR_OFFSET[side]
                opp_node = (x + dx, y + dy, {"N": "S", "E": "W", "S": "N", "W": "E"}[side])
                if opp_node not in feature:
                    open_edges += 1
            if total_edges == 0:
                return 0.0
            return 1.0 - (open_edges / total_edges)
        return 0.5

    def _city_control_bonus(self, board, meeples, player_id, x, y):
        bonus = 0.0
        for side in SIDE_NAMES:
            feature = board.get_feature_containing((x, y, side))
            if feature is None:
                continue
            edge_type = board.feature_graph.nodes[(x, y, side)].get("edge_type")
            if edge_type != EdgeType.CITY:
                continue

            on_feat = meeples.get_meeples_on_feature(feature)
            my_count = sum(1 for m in on_feat if m.player_id == player_id)
            if my_count > 0:
                tile_coords = set((n[0], n[1]) for n in feature)
                has_shield = any(
                    board.grid[c].shield for c in tile_coords if c in board.grid
                )
                bonus += len(tile_coords) * (1.5 if has_shield else 1.0)
        return bonus

    def _aggression_score(self, board, meeples, opponent_id, x, y):
        score = 0.0
        for side in SIDE_NAMES:
            feature = board.get_feature_containing((x, y, side))
            if feature is None:
                continue
            on_feat = meeples.get_meeples_on_feature(feature)
            opp_meeples = [m for m in on_feat if m.player_id == opponent_id]
            if opp_meeples:
                edge_type = board.feature_graph.nodes[(x, y, side)].get("edge_type")
                if edge_type == EdgeType.CITY:
                    completeness = self._feature_completeness(board, feature, edge_type)
                    if completeness < 0.5:
                        score += 2.0
        return score

    def _position_value(self, board, x, y):
        neighbor_count = 0
        for side in SIDE_NAMES:
            dx, dy = NEIGHBOR_OFFSET[side]
            if (x + dx, y + dy) in board.grid:
                neighbor_count += 1
        return neighbor_count * 0.5


def create_bot(bot_type: str = "random", **kwargs):
    if bot_type == "minimax":
        return MinimaxBot(**kwargs)
    return RandomBot()
