import math
import random
import copy
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict

import numpy as np
import networkx as nx
from scipy.spatial import Voronoi
from scipy.stats import entropy as shannon_entropy

from .board import Board
from .tile import (
    TileDef, EdgeType, CenterType, TILE_DEFS,
    SIDE_NAMES, NEIGHBOR_OFFSET, OPPOSITE, create_placed_tile,
)
from .scoring import MeepleManager, Meeple, ScoringEngine


class AnalyticsEngine:
    def __init__(self, board: Board, meeple_mgr: MeepleManager,
                 players: dict, history: list, deck_remaining: int):
        self.board = board
        self.meeples = meeple_mgr
        self.players = players
        self.history = history
        self.deck_remaining = deck_remaining

    def compute_all(self) -> dict:
        return {
            "heatmap": self.heatmap_completion(),
            "luck_curve": self.luck_curve(),
            "entropy": self.field_entropy(),
            "greed_index": self.greed_index(),
            "conflict_risk": self.conflict_risk(),
            "aggression_index": self.aggression_index(),
            "voronoi_control": self.voronoi_control(),
            "nash_distance": self.nash_distance(),
            "parasitism": self.parasitism(),
            "depth_score": self.depth_score(),
        }

    # ── Metric 1: Heatmap Completion (Monte Carlo) ──

    def heatmap_completion(self, n_simulations: int = 200) -> dict:
        city_features = self.board.get_features(EdgeType.CITY)
        incomplete_cities = []
        for f in city_features:
            if not self.board.is_feature_complete(f, EdgeType.CITY):
                meeples = self.meeples.get_meeples_on_feature(f)
                if meeples:
                    incomplete_cities.append(f)

        if not incomplete_cities:
            return {"cells": {}, "max_prob": 0}

        remaining_defs = []
        for td in TILE_DEFS:
            if td.tile_type == "start":
                continue
            count = td.count
            placed_of_type = sum(
                1 for t in self.board.grid.values() if t.tile_type == td.tile_type
            )
            for _ in range(max(0, count - placed_of_type)):
                remaining_defs.append(td)

        if not remaining_defs:
            return {"cells": {}, "max_prob": 0}

        open_slots = list(self.board.open_slots)
        completion_counts = defaultdict(int)

        for _ in range(n_simulations):
            sim_board = copy.deepcopy(self.board)
            sim_deck = list(remaining_defs)
            random.shuffle(sim_deck)

            placed = 0
            for td in sim_deck[:min(8, len(sim_deck))]:
                sim_slots = list(sim_board.open_slots)
                random.shuffle(sim_slots)
                for coord in sim_slots[:10]:
                    for rot in [0, 90, 180, 270]:
                        if sim_board._is_placement_valid(td, coord, rot):
                            sim_board.place_tile(td, coord, rot)
                            placed += 1
                            break
                    else:
                        continue
                    break

            for f_orig in incomplete_cities:
                sample_node = next(iter(f_orig))
                new_feature = sim_board.get_feature_containing(sample_node)
                if new_feature and sim_board.is_feature_complete(new_feature, EdgeType.CITY):
                    tiles = set((n[0], n[1]) for n in new_feature)
                    for t in tiles:
                        key = f"{t[0]},{t[1]}"
                        completion_counts[key] += 1

        cells = {}
        max_prob = 0
        for key, count in completion_counts.items():
            prob = count / n_simulations
            cells[key] = round(prob, 3)
            max_prob = max(max_prob, prob)

        return {"cells": cells, "max_prob": round(max_prob, 3)}

    # ── Metric 2: Luck Curve ──

    def luck_curve(self) -> dict:
        if not self.history:
            return {"players": {}}

        tile_values = {}
        for td in TILE_DEFS:
            value = 0
            for e in td.edges:
                if e == EdgeType.CITY:
                    value += 2
                elif e == EdgeType.ROAD:
                    value += 1
            if td.center == CenterType.MONASTERY:
                value += 3
            if td.shield:
                value += 2
            tile_values[td.tile_type] = value

        avg_value = np.mean(list(tile_values.values())) if tile_values else 1.0

        player_luck = defaultdict(list)
        for move in self.history:
            pid = move["player_id"]
            ttype = move["tile_type"]
            val = tile_values.get(ttype, avg_value)
            deviation = (val - avg_value) / max(avg_value, 1)
            player_luck[pid].append(round(deviation, 3))

        result = {}
        for pid, deviations in player_luck.items():
            cumulative = []
            running = 0
            for d in deviations:
                running += d
                cumulative.append(round(running, 3))
            result[pid] = {
                "per_turn": deviations,
                "cumulative": cumulative,
                "avg": round(np.mean(deviations), 3) if deviations else 0,
            }

        return {"players": result}

    # ── Metric 3: Field Entropy ──

    def field_entropy(self) -> dict:
        open_slots = list(self.board.open_slots)
        if not open_slots:
            return {"entropy": 0, "max_entropy": 0, "normalized": 0}

        compatibility_counts = []
        for coord in open_slots:
            count = 0
            for td in TILE_DEFS:
                if td.tile_type == "start":
                    continue
                for rot in [0, 90, 180, 270]:
                    if self.board._is_placement_valid(td, coord, rot):
                        count += 1
                        break
            compatibility_counts.append(count)

        total = sum(compatibility_counts)
        if total == 0:
            return {"entropy": 0, "max_entropy": 0, "normalized": 0}

        probs = np.array(compatibility_counts, dtype=float) / total
        probs = probs[probs > 0]
        ent = float(shannon_entropy(probs, base=2))
        max_ent = math.log2(len(open_slots)) if len(open_slots) > 1 else 1

        return {
            "entropy": round(ent, 3),
            "max_entropy": round(max_ent, 3),
            "normalized": round(ent / max_ent, 3) if max_ent > 0 else 0,
            "open_slots": len(open_slots),
        }

    # ── Metric 4: Greed Index ──

    def greed_index(self) -> dict:
        result = {}
        for pid, player in self.players.items():
            current_score = player.score

            potential = 0
            player_meeples = self.meeples.get_player_meeples(pid)
            for m in player_meeples:
                feature = self.board.get_feature_containing(m.node_id)
                if feature is None:
                    if m.position == "CENTER":
                        neighbors = sum(
                            1 for dx in [-1, 0, 1] for dy in [-1, 0, 1]
                            if (m.x + dx, m.y + dy) in self.board.grid
                        )
                        potential += neighbors
                    continue
                tile_coords = set((n[0], n[1]) for n in feature)
                edge_type = self.board.feature_graph.nodes[m.node_id].get("edge_type") if m.position != "CENTER" else -1
                if edge_type == EdgeType.CITY:
                    potential += len(tile_coords) * 2
                elif edge_type == EdgeType.ROAD:
                    potential += len(tile_coords)

            total = current_score + potential
            greed = current_score / total if total > 0 else 0.5

            result[pid] = {
                "current_score": current_score,
                "potential": round(potential, 1),
                "greed_index": round(greed, 3),
            }

        return result

    # ── Metric 5: Conflict Risk ──

    def conflict_risk(self) -> dict:
        city_features = self.board.get_features(EdgeType.CITY)
        incomplete = []
        for f in city_features:
            if not self.board.is_feature_complete(f, EdgeType.CITY):
                incomplete.append(f)

        risks = []
        for i, f1 in enumerate(incomplete):
            for j, f2 in enumerate(incomplete):
                if j <= i:
                    continue

                m1 = self.meeples.get_meeples_on_feature(f1)
                m2 = self.meeples.get_meeples_on_feature(f2)
                if not m1 or not m2:
                    continue

                owners1 = set(m.player_id for m in m1)
                owners2 = set(m.player_id for m in m2)
                if owners1 == owners2:
                    continue

                tiles1 = set((n[0], n[1]) for n in f1)
                tiles2 = set((n[0], n[1]) for n in f2)
                min_dist = self._min_feature_distance(tiles1, tiles2)

                if min_dist <= 2:
                    risks.append({
                        "feature1_size": len(tiles1),
                        "feature2_size": len(tiles2),
                        "distance": min_dist,
                        "risk": round(1.0 / (min_dist + 1), 3),
                    })

        total_risk = sum(r["risk"] for r in risks)
        return {
            "conflicts": risks,
            "total_risk": round(total_risk, 3),
            "count": len(risks),
        }

    def _min_feature_distance(self, tiles1: set, tiles2: set) -> int:
        min_d = 999
        for t1 in tiles1:
            for t2 in tiles2:
                d = abs(t1[0] - t2[0]) + abs(t1[1] - t2[1])
                min_d = min(min_d, d)
        return min_d

    # ── Metric 6: Aggression Index ──

    def aggression_index(self) -> dict:
        if len(self.history) < 2:
            return {pid: {"index": 0, "aggressive_moves": 0} for pid in self.players}

        result = {}
        for pid in self.players:
            player_moves = [m for m in self.history if m["player_id"] == pid]
            aggressive = 0

            for move in player_moves:
                x, y = move["x"], move["y"]
                if (x, y) not in self.board.grid:
                    continue
                tile = self.board.grid[(x, y)]
                edges = tile.get_rotated_edges()

                for i, side in enumerate(SIDE_NAMES):
                    if edges[i] != EdgeType.CITY:
                        continue
                    feature = self.board.get_feature_containing((x, y, side))
                    if feature is None:
                        continue
                    on_feat = self.meeples.get_meeples_on_feature(feature)
                    opp_meeples = [m for m in on_feat if m.player_id != pid]
                    if opp_meeples:
                        if not self.board.is_feature_complete(feature, EdgeType.CITY):
                            open_edges = sum(
                                1 for n in feature
                                if (n[0] + NEIGHBOR_OFFSET[n[2]][0],
                                    n[1] + NEIGHBOR_OFFSET[n[2]][1],
                                    OPPOSITE[n[2]]) not in feature
                            )
                            if open_edges >= len(feature) * 0.6:
                                aggressive += 1

            total = len(player_moves) or 1
            result[pid] = {
                "index": round(aggressive / total, 3),
                "aggressive_moves": aggressive,
                "total_moves": len(player_moves),
            }

        return result

    # ── Metric 7: Voronoi Control ──

    def voronoi_control(self) -> dict:
        all_meeples = self.meeples.placed
        if len(all_meeples) < 2:
            return {pid: {"control": 0, "area": 0} for pid in self.players}

        open_slots = list(self.board.open_slots)
        if not open_slots:
            return {pid: {"control": 0, "area": 0} for pid in self.players}

        control = defaultdict(int)
        total = len(open_slots)

        for slot in open_slots:
            sx, sy = slot
            min_dist = 999
            closest_pid = None

            for m in all_meeples:
                d = abs(sx - m.x) + abs(sy - m.y)
                if d < min_dist:
                    min_dist = d
                    closest_pid = m.player_id

            if closest_pid:
                control[closest_pid] += 1

        result = {}
        for pid in self.players:
            area = control.get(pid, 0)
            result[pid] = {
                "control": round(area / total, 3) if total > 0 else 0,
                "area": area,
                "total_slots": total,
            }

        return result

    # ── Metric 8: Nash Distance ──

    def nash_distance(self) -> dict:
        if len(self.history) < 2:
            return {pid: {"distance": 0, "per_turn": []} for pid in self.players}

        from .bots import MinimaxBot
        bot = MinimaxBot(max_depth=1, max_moves_sample=10)

        result = {}
        for pid in self.players:
            distances = []
            player_moves = [m for m in self.history if m["player_id"] == pid]

            sample_moves = player_moves[-5:] if len(player_moves) > 5 else player_moves

            for move in sample_moves:
                actual_x, actual_y, actual_rot = move["x"], move["y"], move["rotation"]
                actual_score = self._move_heuristic(actual_x, actual_y, pid)

                best_possible = actual_score
                neighbors = []
                for side in SIDE_NAMES:
                    dx, dy = NEIGHBOR_OFFSET[side]
                    nx, ny = actual_x + dx, actual_y + dy
                    h = self._move_heuristic(nx, ny, pid)
                    if h > best_possible:
                        best_possible = h

                dist = max(0, best_possible - actual_score)
                distances.append(round(dist, 2))

            avg_dist = np.mean(distances) if distances else 0
            result[pid] = {
                "distance": round(float(avg_dist), 3),
                "per_turn": distances,
            }

        return result

    def _move_heuristic(self, x, y, player_id):
        score = 0
        if (x, y) not in self.board.grid:
            return 0

        tile = self.board.grid[(x, y)]
        edges = tile.get_rotated_edges()
        for i, side in enumerate(SIDE_NAMES):
            if edges[i] == EdgeType.CITY:
                feature = self.board.get_feature_containing((x, y, side))
                if feature:
                    my_m = [m for m in self.meeples.get_meeples_on_feature(feature)
                            if m.player_id == player_id]
                    if my_m:
                        tiles = set((n[0], n[1]) for n in feature)
                        score += len(tiles) * 2
            elif edges[i] == EdgeType.ROAD:
                feature = self.board.get_feature_containing((x, y, side))
                if feature:
                    my_m = [m for m in self.meeples.get_meeples_on_feature(feature)
                            if m.player_id == player_id]
                    if my_m:
                        tiles = set((n[0], n[1]) for n in feature)
                        score += len(tiles)
        return score

    # ── Metric 9: Parasitism ──

    def parasitism(self) -> dict:
        result = {}
        for pid in self.players:
            total_scored = 0
            parasite_scored = 0

            for event in getattr(self, '_score_events', []):
                if event.get("player_id") != pid:
                    continue
                pts = event.get("points", 0)
                total_scored += pts
                if event.get("reason", "").startswith("completed_"):
                    feat_type = event.get("feature_type")
                    if feat_type in ("city", "road"):
                        pass

        for pid in self.players:
            player_meeples = self.meeples.get_player_meeples(pid)
            shared = 0
            total_features = 0

            for m in player_meeples:
                feature = self.board.get_feature_containing(m.node_id)
                if feature is None:
                    continue
                total_features += 1
                on_feat = self.meeples.get_meeples_on_feature(feature)
                other_players = set(mm.player_id for mm in on_feat if mm.player_id != pid)
                if other_players:
                    shared += 1

            result[pid] = {
                "parasitism": round(shared / total_features, 3) if total_features > 0 else 0,
                "shared_features": shared,
                "total_features": total_features,
            }

        return result

    # ── Metric 10: Depth Score (Local vs Global) ──

    def depth_score(self) -> dict:
        if len(self.history) < 3:
            return {pid: {"depth": 0.5, "local_moves": 0, "setup_moves": 0}
                    for pid in self.players}

        result = {}
        for pid in self.players:
            player_moves = [m for m in self.history if m["player_id"] == pid]
            local_count = 0
            setup_count = 0

            score_turns = set()
            for ev in getattr(self, '_score_events', []):
                if ev.get("player_id") == pid:
                    score_turns.add(ev.get("turn", -1))

            for i, move in enumerate(player_moves):
                turn = move["turn"]
                x, y = move["x"], move["y"]

                scored_this_turn = turn in score_turns

                extends_feature = False
                if (x, y) in self.board.grid:
                    tile = self.board.grid[(x, y)]
                    edges = tile.get_rotated_edges()
                    for si, side in enumerate(SIDE_NAMES):
                        if edges[si] in (EdgeType.CITY, EdgeType.ROAD):
                            feat = self.board.get_feature_containing((x, y, side))
                            if feat:
                                my_m = [m for m in self.meeples.get_meeples_on_feature(feat)
                                         if m.player_id == pid]
                                if my_m:
                                    extends_feature = True
                                    break

                if scored_this_turn:
                    local_count += 1
                elif extends_feature:
                    setup_count += 1
                else:
                    setup_count += 0.5

            total = local_count + setup_count
            depth = setup_count / total if total > 0 else 0.5

            result[pid] = {
                "depth": round(depth, 3),
                "local_moves": local_count,
                "setup_moves": round(setup_count, 1),
                "interpretation": "strategic" if depth > 0.6 else "tactical" if depth < 0.3 else "balanced",
            }

        return result


def compute_analytics(board, meeple_mgr, players, history, deck_remaining) -> dict:
    engine = AnalyticsEngine(board, meeple_mgr, players, history, deck_remaining)
    return engine.compute_all()
