from __future__ import annotations
from typing import Optional

from game.engine import Game, Action, GameResult
from game.strategy import evaluate_action
from data.database import Database
from data.repository import PlayerRepo, SessionRepo, RoundRepo, MoveRepo, AnalyticsRepo
from ml.trainer import MLTrainer
from ml.predictor import MLPredictor


class GameSession:
    """
    Ties the game engine to the database. The UI only talks to this class.

    Usage:
        gs = GameSession()
        gs.new_round()
        gs.act(Action.HIT)
        result = gs.finish_round()
    """

    def __init__(self, db: Optional[Database] = None, num_decks: int = 6):
        self.db = db or Database()
        self._player_repo  = PlayerRepo(self.db)
        self._session_repo = SessionRepo(self.db)
        self._round_repo   = RoundRepo(self.db)
        self._move_repo    = MoveRepo(self.db)

        self.player_id  = self._player_repo.get_or_create_default()
        self.session_id = self._session_repo.start(self.player_id, num_decks)

        self._engine    = Game(num_decks)
        self._round_id: Optional[int] = None
        self._round_num = 0
        self._move_num  = 0

        self._moves_total   = 0
        self._moves_correct = 0

        self.last_action:  Optional[Action] = None
        self.last_optimal: Optional[Action] = None
        self.last_correct: Optional[bool]   = None

        self._trainer   = MLTrainer(player_id=self.player_id)
        self._predictor = MLPredictor(self._trainer)
        self._try_train()  # train on existing data if we have enough

    def new_round(self) -> None:
        self._engine.new_round()
        self._round_num += 1
        self._move_num   = 0
        self._moves_total   = 0
        self._moves_correct = 0
        self.last_action  = None
        self.last_optimal = None
        self.last_correct = None

        ph = self._engine.player_hand
        dh = self._engine.dealer_hand

        self._round_id = self._round_repo.start(
            session_id         = self.session_id,
            round_num          = self._round_num,
            player_cards_start = [str(c) for c in ph.cards],  # type: ignore
            dealer_upcard      = str(dh.cards[0]),             # type: ignore
            dealer_hole_card   = str(dh.cards[1]),             # type: ignore
        )

    @property
    def round_active(self) -> bool:
        return self._engine.round_active

    def act(self, action: Action) -> dict:
        """Execute a player action, save it to DB, return feedback."""
        ph    = self._engine._active_hand
        upcard = self._engine.dealer_upcard
        pair_card_val = ph.cards[0].value if ph.is_pair else 0

        # Evaluate before executing so we can compare to optimal
        is_correct, optimal = evaluate_action(
            action          = action,
            player_total    = ph.value,
            dealer_upcard   = upcard.value if upcard else 0,  # type: ignore
            is_soft         = ph.is_soft,
            is_pair         = ph.is_pair,
            pair_card_value = pair_card_val,
        )

        self._move_num      += 1
        self._moves_total   += 1
        self._moves_correct += int(is_correct)

        self._move_repo.record(
            round_id          = self._round_id,       # type: ignore
            move_num          = self._move_num,
            player_total      = ph.value,
            dealer_upcard_val = upcard.value if upcard else 0,  # type: ignore
            is_soft           = ph.is_soft,
            is_pair           = ph.is_pair,
            pair_card_value   = pair_card_val,
            hand_cards        = [str(c) for c in ph.cards],
            action_taken      = action.value,
            optimal_action    = optimal.value,
            is_correct        = is_correct,
        )

        bust_result = self._engine.player_action(action)

        self.last_action  = action
        self.last_optimal = optimal
        self.last_correct = is_correct

        return {
            "action":       action,
            "optimal":      optimal,
            "correct":      is_correct,
            "bust":         bust_result == GameResult.BUST,
            "round_active": self._engine.round_active,
        }

    def finish_round(self) -> dict:
        """Dealer plays out, we determine the result and save everything."""
        result = self._engine.dealer_play()

        ph = self._engine._active_hand
        dh = self._engine.dealer_hand

        self._round_repo.finish(
            round_id           = self._round_id,  # type: ignore
            player_cards_final = [str(c) for c in ph.cards],
            dealer_cards_final = [str(c) for c in dh.cards],  # type: ignore
            player_final_value = ph.value,
            dealer_final_value = dh.value,        # type: ignore
            result             = result.value,
            moves_total        = self._moves_total,
            moves_correct      = self._moves_correct,
        )

        self._player_repo.update_stats(self.player_id, result.value)
        self._try_train()  # retrain every 25 new moves

        accuracy = (
            self._moves_correct / self._moves_total
            if self._moves_total > 0 else 1.0
        )

        return {
            "result":       result,
            "player_value": ph.value,
            "dealer_value": dh.value,  # type: ignore
            "accuracy":     accuracy,
        }

    def end_session(self) -> None:
        self._session_repo.end(self.session_id)

    # ML methods

    def _try_train(self) -> None:
        try:
            moves = self._move_repo.all_for_player(self.player_id)
            if self._trainer.needs_retrain(len(moves)):
                if len(moves) < 50:
                    # Not enough real data yet — pad with synthetic moves
                    from ml.bootstrap import generate_synthetic_moves
                    synthetic = generate_synthetic_moves(200, error_rate=0.35)
                    moves = synthetic + moves
                self._trainer.train(moves)
        except Exception:
            pass  # ML is optional, never break the game

    def ml_warning(self) -> Optional[str]:
        """Return a warning string if the model thinks an error is likely (>60%), else None."""
        try:
            ph     = self._engine._active_hand
            upcard = self._engine.dealer_upcard
            if upcard is None:
                return None

            from game.strategy import get_optimal_action
            optimal = get_optimal_action(
                ph.value, upcard.value, ph.is_soft, ph.is_pair,
                ph.cards[0].value if ph.is_pair else 0
            )

            prob = self._predictor.error_probability(
                player_total      = ph.value,
                dealer_upcard_val = upcard.value,
                is_soft           = ph.is_soft,
                is_pair           = ph.is_pair,
                pair_card_value   = ph.cards[0].value if ph.is_pair else 0,
                action_taken      = optimal.value,
            )
            if self._predictor.should_warn(prob):
                return self._predictor.get_warning_message(prob)
        except Exception:
            pass
        return None

    def ml_cluster(self) -> Optional[dict]:
        """Return the player's play-style cluster from KMeans, or None if not trained yet."""
        try:
            moves = self._move_repo.all_for_player(self.player_id)
            return self._predictor.get_cluster_info(moves)
        except Exception:
            return None

    def ml_top_mistakes(self, n: int = 5) -> list[dict]:
        """Return the top N situations where the player is most likely to make a mistake."""
        try:
            moves = self._move_repo.all_for_player(self.player_id)
            return self._predictor.top_mistakes(moves, n)
        except Exception:
            return []

    @property
    def state(self) -> dict:
        """Full snapshot of the current hand for the UI to render."""
        ph     = self._engine._active_hand
        dh     = self._engine.dealer_hand
        upcard = self._engine.dealer_upcard

        from game.strategy import get_optimal_action
        optimal = get_optimal_action(
            player_total    = ph.value,
            dealer_upcard   = upcard.value if upcard else 0,  # type: ignore
            is_soft         = ph.is_soft,
            is_pair         = ph.is_pair,
            pair_card_value = ph.cards[0].value if ph.is_pair else 0,
        )

        return {
            "player_cards":   [str(c) for c in ph.cards],
            "dealer_upcard":  str(upcard) if upcard else "?",
            "dealer_hidden":  "🂠",
            "player_value":   ph.value,
            "is_soft":        ph.is_soft,
            "is_pair":        ph.is_pair,
            "is_bust":        ph.is_bust,
            "is_blackjack":   ph.is_blackjack,
            "can_double":     ph.can_double,
            "can_split":      ph.can_split,
            "optimal_action": optimal,
            "last_action":    self.last_action,
            "last_optimal":   self.last_optimal,
            "last_correct":   self.last_correct,
            "round_num":      self._round_num,
            "round_active":   self._engine.round_active,
        }
