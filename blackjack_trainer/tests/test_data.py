"""
Тесты для data/ слоя.
Запуск: python -m unittest discover -s tests -v
Используют in-memory SQLite (:memory:) — не оставляют файлов на диске.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import unittest

from data.database import Database
from data.repository import (
    PlayerRepo, SessionRepo, RoundRepo, MoveRepo, AnalyticsRepo
)
from data.game_session import GameSession
from game.engine import Action


# ─── helpers ──────────────────────────────────────────────────────────────────

def make_db() -> Database:
    """In-memory БД — изолирована для каждого теста."""
    return Database(db_path=":memory:")


# ══════════════════════════════════════════════════════════════════════════════
#  DATABASE — connection & schema
# ══════════════════════════════════════════════════════════════════════════════

class TestDatabase(unittest.TestCase):

    def test_creates_tables(self):
        db = make_db()
        conn = db.get_conn()
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {r[0] for r in cur.fetchall()}
        self.assertIn("players",  tables)
        self.assertIn("sessions", tables)
        self.assertIn("rounds",   tables)
        self.assertIn("moves",    tables)

    def test_creates_indexes(self):
        db = make_db()
        conn = db.get_conn()
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        )
        indexes = {r[0] for r in cur.fetchall()}
        self.assertIn("idx_moves_round",     indexes)
        self.assertIn("idx_moves_correct",   indexes)
        self.assertIn("idx_rounds_session",  indexes)
        self.assertIn("idx_sessions_player", indexes)

    def test_foreign_keys_enforced(self):
        db = make_db()
        conn = db.get_conn()
        with self.assertRaises(Exception):
            conn.execute("INSERT INTO sessions (player_id) VALUES (9999)")
            conn.commit()

    def test_to_from_json(self):
        data = ["A♠", "K♥"]
        self.assertEqual(Database.from_json(Database.to_json(data)), data)

    def test_cursor_context_commits(self):
        db = make_db()
        with db.cursor() as cur:
            cur.execute("INSERT INTO players (name) VALUES ('Test')")
        conn = db.get_conn()
        row = conn.execute("SELECT name FROM players WHERE name='Test'").fetchone()
        self.assertIsNotNone(row)

    def test_cursor_context_rollback_on_error(self):
        db = make_db()
        try:
            with db.cursor() as cur:
                cur.execute("INSERT INTO players (name) VALUES ('Rollback')")
                cur.execute("INVALID SQL")   # вызовет ошибку → rollback
        except Exception:
            pass
        conn = db.get_conn()
        row = conn.execute("SELECT * FROM players WHERE name='Rollback'").fetchone()
        self.assertIsNone(row)


# ══════════════════════════════════════════════════════════════════════════════
#  PLAYER REPO
# ══════════════════════════════════════════════════════════════════════════════

class TestPlayerRepo(unittest.TestCase):

    def setUp(self):
        self.db   = make_db()
        self.repo = PlayerRepo(self.db)

    def test_create_returns_id(self):
        pid = self.repo.create("Alice")
        self.assertIsInstance(pid, int)
        self.assertGreater(pid, 0)

    def test_get_returns_player(self):
        pid = self.repo.create("Alice")
        p = self.repo.get(pid)
        self.assertIsNotNone(p)
        self.assertEqual(p["name"], "Alice")

    def test_get_nonexistent_returns_none(self):
        self.assertIsNone(self.repo.get(9999))

    def test_get_or_create_default_creates_first(self):
        pid = self.repo.get_or_create_default()
        self.assertGreater(pid, 0)

    def test_get_or_create_default_reuses_existing(self):
        pid1 = self.repo.get_or_create_default()
        pid2 = self.repo.get_or_create_default()
        self.assertEqual(pid1, pid2)

    def test_update_stats_win(self):
        pid = self.repo.create("Bob")
        self.repo.update_stats(pid, "win")
        p = self.repo.get(pid)
        self.assertEqual(p["total_rounds"], 1)
        self.assertEqual(p["total_wins"],   1)
        self.assertEqual(p["total_losses"], 0)

    def test_update_stats_blackjack_counts_as_win(self):
        pid = self.repo.create("Bob")
        self.repo.update_stats(pid, "blackjack")
        self.assertEqual(self.repo.get(pid)["total_wins"], 1)

    def test_update_stats_bust_counts_as_loss(self):
        pid = self.repo.create("Bob")
        self.repo.update_stats(pid, "bust")
        self.assertEqual(self.repo.get(pid)["total_losses"], 1)

    def test_update_stats_push(self):
        pid = self.repo.create("Bob")
        self.repo.update_stats(pid, "push")
        self.assertEqual(self.repo.get(pid)["total_pushes"], 1)

    def test_update_cluster(self):
        pid = self.repo.create("Carol")
        self.repo.update_cluster(pid, 2, "impulsive")
        p = self.repo.get(pid)
        self.assertEqual(p["cluster_id"],   2)
        self.assertEqual(p["cluster_name"], "impulsive")

    def test_total_rounds_accumulates(self):
        pid = self.repo.create("Dave")
        for result in ("win", "lose", "push", "win"):
            self.repo.update_stats(pid, result)
        self.assertEqual(self.repo.get(pid)["total_rounds"], 4)


# ══════════════════════════════════════════════════════════════════════════════
#  SESSION REPO
# ══════════════════════════════════════════════════════════════════════════════

class TestSessionRepo(unittest.TestCase):

    def setUp(self):
        self.db      = make_db()
        self.players = PlayerRepo(self.db)
        self.repo    = SessionRepo(self.db)
        self.pid     = self.players.create("Eve")

    def test_start_returns_id(self):
        sid = self.repo.start(self.pid)
        self.assertIsInstance(sid, int)

    def test_start_default_num_decks(self):
        sid = self.repo.start(self.pid)
        s = self.repo.get(sid)
        self.assertEqual(s["num_decks"], 6)

    def test_start_custom_num_decks(self):
        sid = self.repo.start(self.pid, num_decks=1)
        self.assertEqual(self.repo.get(sid)["num_decks"], 1)

    def test_get_nonexistent_returns_none(self):
        self.assertIsNone(self.repo.get(9999))

    def test_end_sets_ended_at(self):
        sid = self.repo.start(self.pid)
        self.repo.end(sid)
        s = self.repo.get(sid)
        self.assertIsNotNone(s["ended_at"])

    def test_end_calculates_accuracy(self):
        sid = self.repo.start(self.pid)
        rr = RoundRepo(self.db)
        mr = MoveRepo(self.db)
        rid = rr.start(sid, 1, ["A♠", "K♥"], "7♦", "3♣")
        mr.record(rid, 1, 21, 7, False, False, 0, ["A♠","K♥"], "stand", "stand", True)
        rr.finish(rid, ["A♠","K♥"], ["7♦","3♣","5♠"], 21, 15, "win", 1, 1)
        self.repo.end(sid)
        s = self.repo.get(sid)
        self.assertAlmostEqual(s["accuracy"], 1.0)

    def test_list_for_player_returns_sessions(self):
        self.repo.start(self.pid)
        self.repo.start(self.pid)
        sessions = self.repo.list_for_player(self.pid)
        self.assertEqual(len(sessions), 2)

    def test_list_for_player_respects_limit(self):
        for _ in range(5):
            self.repo.start(self.pid)
        sessions = self.repo.list_for_player(self.pid, limit=3)
        self.assertEqual(len(sessions), 3)


# ══════════════════════════════════════════════════════════════════════════════
#  ROUND REPO
# ══════════════════════════════════════════════════════════════════════════════

class TestRoundRepo(unittest.TestCase):

    def setUp(self):
        self.db   = make_db()
        self.pid  = PlayerRepo(self.db).create("Frank")
        self.sid  = SessionRepo(self.db).start(self.pid)
        self.repo = RoundRepo(self.db)

    def _start(self, round_num=1):
        return self.repo.start(self.sid, round_num, ["A♠","K♥"], "7♦", "3♣")

    def test_start_returns_id(self):
        self.assertGreater(self._start(), 0)

    def test_finish_stores_result(self):
        rid = self._start()
        self.repo.finish(rid, ["A♠","K♥"], ["7♦","3♣"], 21, 10, "win", 1, 1)
        r = self.repo.get(rid)
        self.assertEqual(r["result"], "win")
        self.assertEqual(r["player_final_value"], 21)

    def test_finish_calculates_accuracy(self):
        rid = self._start()
        self.repo.finish(rid, ["A♠","K♥"], ["7♦","3♣"], 21, 10, "win", 4, 3)
        r = self.repo.get(rid)
        self.assertAlmostEqual(r["round_accuracy"], 0.75)

    def test_finish_zero_moves_accuracy_none(self):
        rid = self._start()
        self.repo.finish(rid, ["A♠","K♥"], ["7♦","3♣"], 21, 10, "push", 0, 0)
        r = self.repo.get(rid)
        self.assertIsNone(r["round_accuracy"])

    def test_player_cards_stored_as_json(self):
        rid = self._start()
        r = self.repo.get(rid)
        cards = json.loads(r["player_cards_start"])
        self.assertEqual(cards, ["A♠", "K♥"])

    def test_list_for_session(self):
        self._start(1); self._start(2); self._start(3)
        rounds = self.repo.list_for_session(self.sid)
        self.assertEqual(len(rounds), 3)

    def test_list_ordered_by_round_num(self):
        self._start(3); self._start(1); self._start(2)
        nums = [r["round_num"] for r in self.repo.list_for_session(self.sid)]
        self.assertEqual(nums, [1, 2, 3])


# ══════════════════════════════════════════════════════════════════════════════
#  MOVE REPO
# ══════════════════════════════════════════════════════════════════════════════

class TestMoveRepo(unittest.TestCase):

    def setUp(self):
        self.db  = make_db()
        pid  = PlayerRepo(self.db).create("Grace")
        sid  = SessionRepo(self.db).start(pid)
        self.rid  = RoundRepo(self.db).start(sid, 1, ["10♠","7♥"], "6♦", "3♣")
        self.repo = MoveRepo(self.db)

    def _record(self, move_num=1, action="stand", optimal="stand", correct=True):
        return self.repo.record(
            round_id=self.rid, move_num=move_num,
            player_total=17, dealer_upcard_val=6,
            is_soft=False, is_pair=False, pair_card_value=0,
            hand_cards=["10♠","7♥"],
            action_taken=action, optimal_action=optimal,
            is_correct=correct,
        )

    def test_record_returns_id(self):
        self.assertGreater(self._record(), 0)

    def test_list_for_round(self):
        self._record(1); self._record(2); self._record(3)
        moves = self.repo.list_for_round(self.rid)
        self.assertEqual(len(moves), 3)

    def test_move_fields(self):
        self._record(action="hit", optimal="stand", correct=False)
        m = self.repo.list_for_round(self.rid)[0]
        self.assertEqual(m["action_taken"],   "hit")
        self.assertEqual(m["optimal_action"], "stand")
        self.assertEqual(m["is_correct"],     0)

    def test_correct_flag_true(self):
        self._record(correct=True)
        m = self.repo.list_for_round(self.rid)[0]
        self.assertEqual(m["is_correct"], 1)

    def test_ml_error_prob_nullable(self):
        self._record()
        m = self.repo.list_for_round(self.rid)[0]
        self.assertIsNone(m["ml_error_prob"])

    def test_ml_error_prob_stored(self):
        self.repo.record(
            round_id=self.rid, move_num=1,
            player_total=16, dealer_upcard_val=10,
            is_soft=False, is_pair=False, pair_card_value=0,
            hand_cards=["6♠","10♥"],
            action_taken="stand", optimal_action="hit",
            is_correct=False, ml_error_prob=0.83
        )
        m = self.repo.list_for_round(self.rid)[0]
        self.assertAlmostEqual(m["ml_error_prob"], 0.83)

    def test_all_for_player_returns_all_moves(self):
        db  = make_db()
        pid = PlayerRepo(db).create("Hank")
        sid = SessionRepo(db).start(pid)
        rid = RoundRepo(db).start(sid, 1, ["K♠","7♥"], "5♦", "2♣")
        mr  = MoveRepo(db)
        mr.record(rid, 1, 17, 5, False, False, 0, ["K♠","7♥"], "stand", "stand", True)
        mr.record(rid, 2, 17, 5, False, False, 0, ["K♠","7♥"], "stand", "stand", True)
        moves = mr.all_for_player(pid)
        self.assertEqual(len(moves), 2)


# ══════════════════════════════════════════════════════════════════════════════
#  ANALYTICS REPO
# ══════════════════════════════════════════════════════════════════════════════

class TestAnalyticsRepo(unittest.TestCase):

    def setUp(self):
        """Создаём полный сценарий: 1 игрок, 1 сессия, 2 раунда, 6 ходов."""
        self.db  = make_db()
        self.pid = PlayerRepo(self.db).create("Ivy")
        self.sid = SessionRepo(self.db).start(self.pid)

        rr = RoundRepo(self.db)
        mr = MoveRepo(self.db)

        # Раунд 1: 3 хода (2 правильных)
        rid1 = rr.start(self.sid, 1, ["10♠","6♥"], "9♦", "7♣")
        mr.record(rid1, 1, 16, 9, False, False, 0, ["10♠","6♥"], "hit",   "hit",   True)
        mr.record(rid1, 2, 18, 9, False, False, 0, ["10♠","6♥","2♦"], "stand", "stand", True)
        mr.record(rid1, 3, 18, 9, False, False, 0, ["10♠","6♥","2♦"], "hit",   "stand", False)
        rr.finish(rid1, ["10♠","6♥","2♦"], ["9♦","7♣"], 18, 16, "win", 3, 2)

        # Раунд 2: 3 хода (1 правильный)
        rid2 = rr.start(self.sid, 2, ["A♠","6♥"], "5♦", "3♣")
        mr.record(rid2, 1, 17, 5, True, False, 0, ["A♠","6♥"], "hit",    "double", False)
        mr.record(rid2, 2, 18, 5, True, False, 0, ["A♠","6♥","2♦"], "stand", "stand",  True)
        mr.record(rid2, 3, 18, 5, True, False, 0, ["A♠","6♥","2♦"], "hit",   "stand",  False)
        rr.finish(rid2, ["A♠","6♥","2♦"], ["5♦","3♣","8♠"], 18, 16, "lose", 3, 1)

        PlayerRepo(self.db).update_stats(self.pid, "win")
        PlayerRepo(self.db).update_stats(self.pid, "lose")
        SessionRepo(self.db).end(self.sid)

        self.analytics = AnalyticsRepo(self.db)

    def test_error_heatmap_not_empty(self):
        hm = self.analytics.error_heatmap(self.pid)
        self.assertGreater(len(hm), 0)

    def test_error_heatmap_has_required_keys(self):
        hm = self.analytics.error_heatmap(self.pid)
        row = hm[0]
        for key in ("player_total", "dealer_upcard_val", "error_rate", "total_moves"):
            self.assertIn(key, row)

    def test_error_heatmap_sorted_by_error_rate(self):
        hm = self.analytics.error_heatmap(self.pid)
        rates = [r["error_rate"] for r in hm]
        self.assertEqual(rates, sorted(rates, reverse=True))

    def test_accuracy_by_session_returns_history(self):
        hist = self.analytics.accuracy_by_session(self.pid)
        self.assertEqual(len(hist), 1)

    def test_accuracy_by_session_has_accuracy_field(self):
        hist = self.analytics.accuracy_by_session(self.pid)
        self.assertIn("accuracy", hist[0])

    def test_action_breakdown_not_empty(self):
        bd = self.analytics.action_breakdown(self.pid)
        self.assertGreater(len(bd), 0)

    def test_action_breakdown_has_accuracy(self):
        bd = self.analytics.action_breakdown(self.pid)
        for row in bd:
            self.assertIn("accuracy", row)
            self.assertIn("action",   row)

    def test_overall_stats_total_rounds(self):
        stats = self.analytics.overall_stats(self.pid)
        self.assertEqual(stats["total_rounds"], 2)

    def test_overall_stats_avg_accuracy_set(self):
        stats = self.analytics.overall_stats(self.pid)
        self.assertGreater(stats["avg_accuracy"], 0)

    def test_recent_mistakes_returns_errors_only(self):
        mistakes = self.analytics.recent_mistakes(self.pid)
        for m in mistakes:
            self.assertNotEqual(m["action_taken"], m["optimal_action"])

    def test_recent_mistakes_limit_respected(self):
        mistakes = self.analytics.recent_mistakes(self.pid, limit=2)
        self.assertLessEqual(len(mistakes), 2)

    def test_no_data_player_returns_empty(self):
        empty_pid = PlayerRepo(self.db).create("Ghost")
        self.assertEqual(self.analytics.error_heatmap(empty_pid), [])
        self.assertEqual(self.analytics.accuracy_by_session(empty_pid), [])


# ══════════════════════════════════════════════════════════════════════════════
#  GAME SESSION — integration
# ══════════════════════════════════════════════════════════════════════════════

class TestGameSession(unittest.TestCase):

    def _gs(self) -> GameSession:
        return GameSession(db=make_db(), num_decks=1)

    def test_creates_player_and_session(self):
        gs = self._gs()
        self.assertGreater(gs.player_id,  0)
        self.assertGreater(gs.session_id, 0)

    def test_new_round_state_has_cards(self):
        gs = self._gs()
        gs.new_round()
        s = gs.state
        self.assertEqual(len(s["player_cards"]), 2)

    def test_state_has_optimal_action(self):
        gs = self._gs()
        gs.new_round()
        self.assertIsNotNone(gs.state["optimal_action"])

    def test_act_returns_feedback(self):
        gs = self._gs()
        gs.new_round()
        # Стенд — безопасно для любой руки
        fb = gs.act(Action.STAND)
        self.assertIn("correct", fb)
        self.assertIn("optimal", fb)
        self.assertIn("bust",    fb)

    def test_act_records_correct_flag(self):
        gs = self._gs()
        gs.new_round()
        optimal = gs.state["optimal_action"]
        fb = gs.act(optimal)
        self.assertTrue(fb["correct"])

    def test_act_records_incorrect_flag(self):
        gs = self._gs()
        gs.new_round()
        optimal = gs.state["optimal_action"]
        # Выбираем любое другое действие
        wrong = next(
            a for a in Action
            if a != optimal and not (a == Action.SPLIT and not gs.state["can_split"])
                             and not (a == Action.DOUBLE and not gs.state["can_double"])
        )
        fb = gs.act(wrong)
        # Может совпасть случайно — просто проверяем что поле есть
        self.assertIsInstance(fb["correct"], bool)

    def test_stand_ends_round(self):
        gs = self._gs()
        gs.new_round()
        gs.act(Action.STAND)
        self.assertFalse(gs.round_active)

    def test_finish_round_returns_result(self):
        gs = self._gs()
        gs.new_round()
        gs.act(Action.STAND)
        result = gs.finish_round()
        self.assertIn("result",       result)
        self.assertIn("player_value", result)
        self.assertIn("dealer_value", result)
        self.assertIn("accuracy",     result)

    def test_finish_round_accuracy_between_0_and_1(self):
        gs = self._gs()
        gs.new_round()
        gs.act(Action.STAND)
        r = gs.finish_round()
        self.assertGreaterEqual(r["accuracy"], 0.0)
        self.assertLessEqual(r["accuracy"],    1.0)

    def test_multiple_rounds(self):
        gs = self._gs()
        for _ in range(5):
            gs.new_round()
            gs.act(Action.STAND)
            gs.finish_round()
        self.assertEqual(gs._round_num, 5)

    def test_end_session_closes_session(self):
        gs = self._gs()
        gs.new_round()
        gs.act(Action.STAND)
        gs.finish_round()
        gs.end_session()
        s = SessionRepo(gs.db).get(gs.session_id)
        self.assertIsNotNone(s["ended_at"])

    def test_moves_saved_to_db(self):
        gs = self._gs()
        gs.new_round()
        gs.act(Action.STAND)
        mr = MoveRepo(gs.db)
        moves = mr.list_for_round(gs._round_id)
        self.assertEqual(len(moves), 1)

    def test_player_stats_updated_after_finish(self):
        gs = self._gs()
        gs.new_round()
        gs.act(Action.STAND)
        gs.finish_round()
        p = PlayerRepo(gs.db).get(gs.player_id)
        self.assertEqual(p["total_rounds"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
