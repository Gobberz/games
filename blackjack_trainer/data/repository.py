from __future__ import annotations
import json
from typing import Optional

from data.database import Database


class PlayerRepo:
    def __init__(self, db: Database):
        self.db = db

    def create(self, name: str = "Player") -> int:
        with self.db.cursor() as cur:
            cur.execute("INSERT INTO players (name) VALUES (?)", (name,))
            return cur.lastrowid  # type: ignore

    def get(self, player_id: int) -> Optional[dict]:
        with self.db.cursor() as cur:
            cur.execute("SELECT * FROM players WHERE id = ?", (player_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_or_create_default(self) -> int:
        with self.db.cursor() as cur:
            cur.execute("SELECT id FROM players ORDER BY id LIMIT 1")
            row = cur.fetchone()
            if row:
                return row["id"]
        return self.create("Player")

    def update_stats(self, player_id: int, result: str) -> None:
        col_map = {
            "win":       "total_wins",
            "blackjack": "total_wins",
            "lose":      "total_losses",
            "bust":      "total_losses",
            "push":      "total_pushes",
        }
        col = col_map.get(result, "total_losses")
        with self.db.cursor() as cur:
            cur.execute(
                f"UPDATE players SET total_rounds = total_rounds + 1, "
                f"{col} = {col} + 1 WHERE id = ?",
                (player_id,)
            )

    def update_cluster(self, player_id: int, cluster_id: int, cluster_name: str) -> None:
        with self.db.cursor() as cur:
            cur.execute(
                "UPDATE players SET cluster_id = ?, cluster_name = ? WHERE id = ?",
                (cluster_id, cluster_name, player_id)
            )


class SessionRepo:
    def __init__(self, db: Database):
        self.db = db

    def start(self, player_id: int, num_decks: int = 6) -> int:
        with self.db.cursor() as cur:
            cur.execute(
                "INSERT INTO sessions (player_id, num_decks) VALUES (?, ?)",
                (player_id, num_decks)
            )
            return cur.lastrowid  # type: ignore

    def end(self, session_id: int) -> None:
        with self.db.cursor() as cur:
            cur.execute("""
                UPDATE sessions
                SET
                    ended_at      = datetime('now'),
                    rounds_played = (
                        SELECT COUNT(*) FROM rounds WHERE session_id = ?
                    ),
                    accuracy = (
                        SELECT ROUND(
                            SUM(moves_correct) * 1.0 / NULLIF(SUM(moves_total), 0), 3
                        )
                        FROM rounds WHERE session_id = ?
                    ),
                    win_rate = (
                        SELECT ROUND(
                            SUM(CASE WHEN result IN ('win','blackjack') THEN 1 ELSE 0 END)
                            * 1.0 / NULLIF(COUNT(*), 0), 3
                        )
                        FROM rounds WHERE session_id = ? AND result IS NOT NULL
                    )
                WHERE id = ?
            """, (session_id, session_id, session_id, session_id))


    def list_for_player(self, player_id: int, limit: int = 100) -> list[dict]:
        with self.db.cursor() as cur:
            cur.execute(
                "SELECT * FROM sessions WHERE player_id = ? ORDER BY id DESC LIMIT ?",
                (player_id, limit)
            )
            return [dict(r) for r in cur.fetchall()]

    def get(self, session_id: int) -> Optional[dict]:
        with self.db.cursor() as cur:
            cur.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = cur.fetchone()
            return dict(row) if row else None


class RoundRepo:
    def __init__(self, db: Database):
        self.db = db

    def start(
        self,
        session_id: int,
        round_num: int,
        player_cards_start: list[str],
        dealer_upcard: str,
        dealer_hole_card: str,
    ) -> int:
        with self.db.cursor() as cur:
            cur.execute("""
                INSERT INTO rounds (
                    session_id, round_num,
                    player_cards_start, dealer_upcard, dealer_hole_card
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                session_id, round_num,
                json.dumps(player_cards_start),
                dealer_upcard,
                dealer_hole_card,
            ))
            return cur.lastrowid  # type: ignore

    def finish(
        self,
        round_id: int,
        player_cards_final: list[str],
        dealer_cards_final: list[str],
        player_final_value: int,
        dealer_final_value: int,
        result: str,
        moves_total: int,
        moves_correct: int,
    ) -> None:
        accuracy = moves_correct / moves_total if moves_total > 0 else None
        with self.db.cursor() as cur:
            cur.execute("""
                UPDATE rounds SET
                    player_cards_final  = ?,
                    dealer_cards_final  = ?,
                    player_final_value  = ?,
                    dealer_final_value  = ?,
                    result              = ?,
                    moves_total         = ?,
                    moves_correct       = ?,
                    round_accuracy      = ?
                WHERE id = ?
            """, (
                json.dumps(player_cards_final),
                json.dumps(dealer_cards_final),
                player_final_value,
                dealer_final_value,
                result,
                moves_total,
                moves_correct,
                accuracy,
                round_id,
            ))

    def get(self, round_id: int) -> Optional[dict]:
        with self.db.cursor() as cur:
            cur.execute("SELECT * FROM rounds WHERE id = ?", (round_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def list_for_session(self, session_id: int) -> list[dict]:
        with self.db.cursor() as cur:
            cur.execute(
                "SELECT * FROM rounds WHERE session_id = ? ORDER BY round_num",
                (session_id,)
            )
            return [dict(r) for r in cur.fetchall()]


class MoveRepo:
    def __init__(self, db: Database):
        self.db = db

    def record(
        self,
        round_id: int,
        move_num: int,
        player_total: int,
        dealer_upcard_val: int,
        is_soft: bool,
        is_pair: bool,
        pair_card_value: int,
        hand_cards: list[str],
        action_taken: str,
        optimal_action: str,
        is_correct: bool,
        ml_error_prob: Optional[float] = None,
    ) -> int:
        with self.db.cursor() as cur:
            cur.execute("""
                INSERT INTO moves (
                    round_id, move_num,
                    player_total, dealer_upcard_val,
                    is_soft, is_pair, pair_card_value, hand_cards,
                    action_taken, optimal_action, is_correct,
                    ml_error_prob
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                round_id, move_num,
                player_total, dealer_upcard_val,
                int(is_soft), int(is_pair), pair_card_value,
                json.dumps(hand_cards),
                action_taken, optimal_action, int(is_correct),
                ml_error_prob,
            ))
            return cur.lastrowid  # type: ignore

    def list_for_round(self, round_id: int) -> list[dict]:
        with self.db.cursor() as cur:
            cur.execute(
                "SELECT * FROM moves WHERE round_id = ? ORDER BY move_num",
                (round_id,)
            )
            return [dict(r) for r in cur.fetchall()]

    def all_for_player(self, player_id: int) -> list[dict]:
        """Pull every move this player has ever made — main ML dataset."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT m.*
                FROM moves m
                JOIN rounds   r ON r.id = m.round_id
                JOIN sessions s ON s.id = r.session_id
                WHERE s.player_id = ?
                ORDER BY m.id
            """, (player_id,))
            return [dict(r) for r in cur.fetchall()]


class AnalyticsRepo:
    def __init__(self, db: Database):
        self.db = db

    def error_heatmap(self, player_id: int) -> list[dict]:
        """Error rate per situation (player_total × dealer_upcard) for the heatmap."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT
                    m.player_total,
                    m.dealer_upcard_val,
                    m.is_soft,
                    m.is_pair,
                    COUNT(*)                                            AS total_moves,
                    SUM(CASE WHEN m.is_correct = 0 THEN 1 ELSE 0 END) AS errors,
                    ROUND(
                        SUM(CASE WHEN m.is_correct = 0 THEN 1 ELSE 0 END) * 1.0
                        / NULLIF(COUNT(*), 0), 3
                    )                                                   AS error_rate
                FROM moves m
                JOIN rounds   r ON r.id = m.round_id
                JOIN sessions s ON s.id = r.session_id
                WHERE s.player_id = ?
                GROUP BY m.player_total, m.dealer_upcard_val, m.is_soft, m.is_pair
                ORDER BY error_rate DESC
            """, (player_id,))
            return [dict(r) for r in cur.fetchall()]

    def accuracy_by_session(self, player_id: int) -> list[dict]:
        """Per-session accuracy history for the progress chart."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT
                    s.id            AS session_id,
                    s.started_at,
                    s.rounds_played,
                    COALESCE(s.accuracy, 0)  AS accuracy,
                    COALESCE(s.win_rate, 0)  AS win_rate
                FROM sessions s
                WHERE s.player_id = ? AND s.ended_at IS NOT NULL
                ORDER BY s.started_at
            """, (player_id,))
            return [dict(r) for r in cur.fetchall()]

    def action_breakdown(self, player_id: int) -> list[dict]:
        """Accuracy broken down by action type (hit/stand/double/split)."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT
                    m.optimal_action                                          AS action,
                    COUNT(*)                                                  AS total,
                    SUM(m.is_correct)                                         AS correct,
                    ROUND(SUM(m.is_correct) * 1.0 / NULLIF(COUNT(*), 0), 3)  AS accuracy
                FROM moves m
                JOIN rounds   r ON r.id = m.round_id
                JOIN sessions s ON s.id = r.session_id
                WHERE s.player_id = ?
                GROUP BY m.optimal_action
            """, (player_id,))
            return [dict(r) for r in cur.fetchall()]

    def overall_stats(self, player_id: int) -> dict:
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT
                    p.total_rounds,
                    p.total_wins,
                    p.total_losses,
                    p.total_pushes,
                    p.cluster_name,
                    COUNT(DISTINCT s.id)            AS sessions_count,
                    COALESCE(AVG(s.accuracy), 0)    AS avg_accuracy,
                    COALESCE(AVG(s.win_rate), 0)    AS avg_win_rate
                FROM players p
                LEFT JOIN sessions s ON s.player_id = p.id AND s.ended_at IS NOT NULL
                WHERE p.id = ?
                GROUP BY p.id
            """, (player_id,))
            row = cur.fetchone()
            return dict(row) if row else {}

    def recent_mistakes(self, player_id: int, limit: int = 10) -> list[dict]:
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT
                    m.player_total,
                    m.dealer_upcard_val,
                    m.is_soft,
                    m.is_pair,
                    m.action_taken,
                    m.optimal_action,
                    m.created_at
                FROM moves m
                JOIN rounds   r ON r.id = m.round_id
                JOIN sessions s ON s.id = r.session_id
                WHERE s.player_id = ? AND m.is_correct = 0
                ORDER BY m.id DESC
                LIMIT ?
            """, (player_id, limit))
            return [dict(r) for r in cur.fetchall()]
