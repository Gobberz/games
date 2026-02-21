from typing import Dict, List, Optional, Tuple
from .board import Board
from .deck import Deck
from .tile import TileDef, TILE_DEFS, EdgeType
from .scoring import MeepleManager, Meeple, ScoringEngine, ScoreEvent, MEEPLES_PER_PLAYER
from .bots import create_bot, BotMove
from .analytics import compute_analytics
from .objectives import ObjectiveManager
from .engineer import (
    EngineerManager, get_valid_engineer_targets, apply_engineer_rotation,
)
import uuid


class Player:
    def __init__(self, player_id: str, name: str, is_bot: bool = False, bot_type: str = "random"):
        self.id = player_id
        self.name = name
        self.score = 0
        self.hand: List[TileDef] = []
        self.is_bot = is_bot
        self.bot_type = bot_type
        self.bot = create_bot(bot_type) if is_bot else None

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "score": self.score,
            "hand_size": len(self.hand),
            "hand": [{"tile_type": t.tile_type, "edges": t.edges} for t in self.hand],
            "is_bot": self.is_bot,
            "bot_type": self.bot_type if self.is_bot else None,
        }


class GameSession:
    """
    Game modes (via custom_rules dict):
      - engineer: bool (default True) — each player gets 1 engineer token
      - objectives: bool (default True) — deal 2 hidden objectives
      - hand_size: int (default 2) — strategic reserve tiles in hand
    """

    def __init__(self, game_id: Optional[str] = None, num_players: int = 2,
                 custom_rules: Optional[dict] = None):
        self.id = game_id or str(uuid.uuid4())[:8]
        self.board = Board()
        self.deck = Deck()
        self.meeples = MeepleManager()
        self.scoring = ScoringEngine(self.board, self.meeples)
        self.players: Dict[str, Player] = {}
        self.turn_order: List[str] = []
        self.current_turn_idx: int = 0
        self.phase: str = "waiting"
        self.turn_phase: str = "place_tile"  # place_tile, place_meeple
        self.last_placed_coord: Optional[Tuple[int, int]] = None
        self.num_players = num_players
        self.history: List[dict] = []
        self.score_events: List[dict] = []

        # Custom rules
        rules = custom_rules or {}
        self.rules = {
            "engineer": rules.get("engineer", True),
            "objectives": rules.get("objectives", True),
            "hand_size": rules.get("hand_size", 2),
        }

        # Custom mechanics managers
        self.engineer = EngineerManager() if self.rules["engineer"] else None
        self.objectives = ObjectiveManager() if self.rules["objectives"] else None

    # ── Player Management ──

    def add_player(self, name: str, is_bot: bool = False, bot_type: str = "random") -> Player:
        pid = str(uuid.uuid4())[:8]
        player = Player(pid, name, is_bot, bot_type)
        self.players[pid] = player
        self.turn_order.append(pid)
        self.meeples.init_player(pid)
        if self.engineer:
            self.engineer.init_player(pid)

        if len(self.players) >= self.num_players:
            self._start_game()
        return player

    def _start_game(self):
        self.phase = "playing"
        self.turn_phase = "place_tile"
        hand_size = self.rules["hand_size"]
        for pid in self.turn_order:
            p = self.players[pid]
            for _ in range(hand_size):
                tile = self.deck.draw()
                if tile:
                    p.hand.append(tile)

        if self.objectives:
            self.objectives.deal_objectives(list(self.players.keys()), count=2)

    def current_player(self) -> Optional[Player]:
        if self.phase != "playing" or not self.turn_order:
            return None
        return self.players[self.turn_order[self.current_turn_idx]]

    # ── Core Turn Actions ──

    def make_move(self, player_id: str, tile_idx: int, x: int, y: int, rotation: int) -> dict:
        if self.phase != "playing":
            return {"error": "Game is not in playing phase"}
        if self.turn_phase != "place_tile":
            return {"error": "Must place or skip meeple first"}

        cp = self.current_player()
        if not cp or cp.id != player_id:
            return {"error": "Not your turn"}
        if tile_idx < 0 or tile_idx >= len(cp.hand):
            return {"error": "Invalid tile index"}

        tile_def = cp.hand[tile_idx]
        placed = self.board.place_tile(tile_def, (x, y), rotation)
        if not placed:
            return {"error": "Invalid placement"}

        cp.hand.pop(tile_idx)
        new_tile = self.deck.draw()
        if new_tile:
            cp.hand.append(new_tile)

        self.last_placed_coord = (x, y)

        meeple_nodes = set(m.node_id for m in self.meeples.placed)
        meeple_positions = self.board.get_valid_meeple_positions(x, y, meeple_nodes)
        has_meeple_options = (
            len(meeple_positions) > 0
            and self.meeples.available(player_id) > 0
        )

        if has_meeple_options:
            self.turn_phase = "place_meeple"
        else:
            self._finish_turn()

        move_record = {
            "player_id": player_id,
            "tile_type": tile_def.tile_type,
            "x": x, "y": y,
            "rotation": rotation,
            "turn": len(self.history),
        }
        self.history.append(move_record)

        return {
            "success": True,
            "move": move_record,
            "meeple_options": meeple_positions if has_meeple_options else [],
        }

    def place_meeple(self, player_id: str, position: str) -> dict:
        if self.phase != "playing":
            return {"error": "Game is not in playing phase"}
        if self.turn_phase != "place_meeple":
            return {"error": "Not in meeple placement phase"}
        cp = self.current_player()
        if not cp or cp.id != player_id:
            return {"error": "Not your turn"}
        if not self.last_placed_coord:
            return {"error": "No tile placed this turn"}

        x, y = self.last_placed_coord
        meeple_nodes = set(m.node_id for m in self.meeples.placed)
        valid = self.board.get_valid_meeple_positions(x, y, meeple_nodes)
        valid_positions = {v["position"] for v in valid}

        if position not in valid_positions:
            return {"error": f"Invalid meeple position: {position}"}

        meeple = Meeple(player_id, x, y, position)
        if not self.meeples.place(meeple):
            return {"error": "No meeples available"}

        events = self._finish_turn()
        return {
            "success": True,
            "meeple": {"x": x, "y": y, "position": position},
            "score_events": [self._event_to_dict(e) for e in events],
        }

    def skip_meeple(self, player_id: str) -> dict:
        if self.phase != "playing":
            return {"error": "Game is not in playing phase"}
        if self.turn_phase != "place_meeple":
            return {"error": "Not in meeple placement phase"}
        cp = self.current_player()
        if not cp or cp.id != player_id:
            return {"error": "Not your turn"}

        events = self._finish_turn()
        return {
            "success": True,
            "score_events": [self._event_to_dict(e) for e in events],
        }

    # ── Engineer Action ──

    def use_engineer(self, player_id: str, target_x: int, target_y: int) -> dict:
        if not self.engineer:
            return {"error": "Engineer not enabled"}
        if self.phase != "playing":
            return {"error": "Game is not in playing phase"}
        if self.turn_phase != "place_tile":
            return {"error": "Can only use engineer during tile placement phase"}

        cp = self.current_player()
        if not cp or cp.id != player_id:
            return {"error": "Not your turn"}
        if not self.engineer.has_engineer(player_id):
            return {"error": "Engineer already used"}

        targets = get_valid_engineer_targets(
            self.board, self.meeples.placed, player_id
        )
        valid_coords = {(t["x"], t["y"]) for t in targets}
        if (target_x, target_y) not in valid_coords:
            return {"error": "Invalid engineer target"}

        if not apply_engineer_rotation(self.board, target_x, target_y):
            return {"error": "Rotation failed"}

        self.engineer.use_engineer(player_id)

        self.history.append({
            "player_id": player_id,
            "action": "engineer",
            "x": target_x, "y": target_y,
            "turn": len(self.history),
        })

        events = self.scoring.check_and_score_completed(len(self.history))
        for e in events:
            self.players[e.player_id].score += e.points
            self.score_events.append(self._event_to_dict(e))

        return {
            "success": True,
            "rotated": {"x": target_x, "y": target_y,
                        "new_rotation": self.board.grid[(target_x, target_y)].rotation},
            "score_events": [self._event_to_dict(e) for e in events],
        }

    def get_engineer_targets(self, player_id: str) -> List[dict]:
        if not self.engineer or not self.engineer.has_engineer(player_id):
            return []
        return get_valid_engineer_targets(
            self.board, self.meeples.placed, player_id
        )

    # ── Turn Flow ──

    def _finish_turn(self) -> List[ScoreEvent]:
        turn = len(self.history)
        events = self.scoring.check_and_score_completed(turn)

        for e in events:
            self.players[e.player_id].score += e.points
            self.score_events.append(self._event_to_dict(e))

        self.last_placed_coord = None
        self.turn_phase = "place_tile"
        self.current_turn_idx = (self.current_turn_idx + 1) % len(self.turn_order)

        if self.deck.remaining() == 0 and all(len(p.hand) == 0 for p in self.players.values()):
            self._end_game()

        return events

    def _end_game(self):
        turn = len(self.history)
        end_events = self.scoring.score_end_game(turn)
        for e in end_events:
            self.players[e.player_id].score += e.points
            self.score_events.append(self._event_to_dict(e))

        # Evaluate and award objective bonuses
        if self.objectives:
            self.objectives.evaluate_all(self)
            bonuses = self.objectives.get_bonus_points()
            for pid, pts in bonuses.items():
                if pts > 0:
                    self.players[pid].score += pts
                    self.score_events.append({
                        "player_id": pid, "points": pts,
                        "reason": "objective_bonus", "feature_type": "objective",
                        "tiles": [], "turn": turn,
                    })

        self.phase = "finished"

    # ── Query Methods ──

    def get_valid_moves(self, player_id: str) -> List[dict]:
        cp = self.current_player()
        if not cp or cp.id != player_id:
            return []
        if self.turn_phase != "place_tile":
            return []
        moves = []
        for i, tile_def in enumerate(cp.hand):
            placements = self.board.get_valid_placements(tile_def)
            for (coord, rot) in placements:
                moves.append({
                    "tile_idx": i, "tile_type": tile_def.tile_type,
                    "x": coord[0], "y": coord[1], "rotation": rot,
                })
        return moves

    def get_meeple_options(self, player_id: str) -> List[dict]:
        if self.turn_phase != "place_meeple":
            return []
        cp = self.current_player()
        if not cp or cp.id != player_id:
            return []
        if not self.last_placed_coord:
            return []
        x, y = self.last_placed_coord
        meeple_nodes = set(m.node_id for m in self.meeples.placed)
        return self.board.get_valid_meeple_positions(x, y, meeple_nodes)

    # ── Bot Support ──

    def try_bot_turn(self) -> Optional[dict]:
        cp = self.current_player()
        if not cp or not cp.is_bot or self.phase != "playing":
            return None

        if self.turn_phase == "place_meeple":
            bot_state = self._build_bot_state(cp)
            move = cp.bot.choose_move(bot_state)
            if move and move.meeple_position:
                result = self.place_meeple(cp.id, move.meeple_position)
            else:
                result = self.skip_meeple(cp.id)
            return result

        bot_state = self._build_bot_state(cp)
        move = cp.bot.choose_move(bot_state)
        if not move:
            self.turn_phase = "place_tile"
            self.current_turn_idx = (self.current_turn_idx + 1) % len(self.turn_order)
            return {"skipped": True}

        result = self.make_move(cp.id, move.tile_idx, move.x, move.y, move.rotation)
        if "error" in result:
            return result

        if self.turn_phase == "place_meeple" and move.meeple_position:
            mresult = self.place_meeple(cp.id, move.meeple_position)
            if "error" in mresult:
                self.skip_meeple(cp.id)
        elif self.turn_phase == "place_meeple":
            self.skip_meeple(cp.id)

        return result

    def _build_bot_state(self, player: Player) -> dict:
        placed_nodes = set(m.node_id for m in self.meeples.placed)
        opponent_ids = [pid for pid in self.turn_order if pid != player.id]
        opponent_id = opponent_ids[0] if opponent_ids else player.id
        scores = {pid: p.score for pid, p in self.players.items()}
        return {
            "board": self.board,
            "hand": list(player.hand),
            "player_id": player.id,
            "opponent_id": opponent_id,
            "meeples_available": self.meeples.available(player.id),
            "placed_meeple_nodes": placed_nodes,
            "meeple_mgr": self.meeples,
            "scores": scores,
            "deck_remaining": self.deck.remaining(),
        }

    def get_analytics(self) -> dict:
        return compute_analytics(
            self.board, self.meeples, self.players,
            self.history, self.deck.remaining()
        )

    # ── Serialization ──

    def _event_to_dict(self, e) -> dict:
        if isinstance(e, dict):
            return e
        return {
            "player_id": e.player_id,
            "points": e.points,
            "reason": e.reason,
            "feature_type": e.feature_type,
            "tiles": e.tiles,
            "turn": e.turn,
        }

    def to_dict(self, for_player: Optional[str] = None) -> dict:
        players_data = {}
        for pid, p in self.players.items():
            pd = p.to_dict()
            pd["meeples_available"] = self.meeples.available(pid)
            if self.engineer:
                pd["has_engineer"] = self.engineer.has_engineer(pid)
            if for_player and pid != for_player:
                del pd["hand"]
            players_data[pid] = pd

        result = {
            "id": self.id,
            "phase": self.phase,
            "turn_phase": self.turn_phase,
            "board": self.board.to_dict(),
            "meeples": self.meeples.to_dict(),
            "players": players_data,
            "current_player": self.current_player().id if self.current_player() else None,
            "deck_remaining": self.deck.remaining(),
            "turn": len(self.history),
            "last_placed": list(self.last_placed_coord) if self.last_placed_coord else None,
            "recent_scores": self.score_events[-5:] if self.score_events else [],
            "rules": self.rules,
        }

        if self.engineer:
            result["engineer"] = self.engineer.to_dict()

        if self.objectives and for_player:
            result["objectives"] = self.objectives.to_dict(for_player=for_player)
        elif self.objectives:
            result["objectives"] = self.objectives.to_dict()

        return result
