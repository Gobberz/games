"""
Тесты UI-слоя и симуляции.
Не требуют Streamlit.
"""

import sys, os, types
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Mock streamlit before any ui import
_st_mock = types.ModuleType('streamlit')
_st_mock.cache_resource = lambda f: f
sys.modules['streamlit'] = _st_mock

import unittest
from ui.styles import card_html, hand_html, value_badge, feedback_html, COLORS


class TestCardHtml(unittest.TestCase):
    def test_hidden_card(self):
        html = card_html("A♠", hidden=True)
        self.assertIn("bj-card-hidden", html)
        self.assertIn("🂠", html)
    def test_red_hearts(self):
        self.assertIn("bj-card-red", card_html("A♥"))
    def test_red_diamonds(self):
        self.assertIn("bj-card-red", card_html("K♦"))
    def test_black_spades(self):
        self.assertIn("bj-card-black", card_html("10♠"))
    def test_black_clubs(self):
        self.assertIn("bj-card-black", card_html("7♣"))
    def test_rank_present(self):
        self.assertIn("Q", card_html("Q♠"))
    def test_suit_present(self):
        self.assertIn("♠", card_html("Q♠"))
    def test_returns_string(self):
        self.assertIsInstance(card_html("5♥"), str)


class TestHandHtml(unittest.TestCase):
    def test_two_cards_rendered(self):
        html = hand_html(["A♠", "K♥"])
        self.assertIn("A", html); self.assertIn("K", html)
    def test_show_all_no_hidden(self):
        self.assertNotIn("bj-card-hidden", hand_html(["A♠","K♥"], show_all=True))
    def test_show_second_hidden(self):
        self.assertIn("bj-card-hidden", hand_html(["A♠","K♥"], show_all=False))
    def test_empty_hand(self):
        self.assertEqual(hand_html([]).strip(), "")
    def test_single_card(self):
        self.assertIn("7", hand_html(["7♦"]))
    def test_three_cards(self):
        html = hand_html(["A♠","6♥","3♦"])
        self.assertIn("A", html); self.assertIn("6", html); self.assertIn("3", html)


class TestValueBadge(unittest.TestCase):
    def test_normal_value(self):       self.assertIn("15", value_badge(15))
    def test_bust_color(self):         self.assertIn(COLORS["error"], value_badge(22, is_bust=True))
    def test_blackjack_gold(self):     self.assertIn(COLORS["gold"], value_badge(21))
    def test_soft_label(self):         self.assertIn("Soft", value_badge(17, is_soft=True))
    def test_hard_no_soft(self):       self.assertNotIn("Soft", value_badge(17, is_soft=False))
    def test_high_value_green(self):   self.assertIn(COLORS["success"], value_badge(18))
    def test_returns_string(self):     self.assertIsInstance(value_badge(15), str)


class TestFeedbackHtml(unittest.TestCase):
    def test_correct_class(self):      self.assertIn("feedback-correct", feedback_html(True, "stand","stand"))
    def test_wrong_class(self):        self.assertIn("feedback-wrong",   feedback_html(False,"hit","stand"))
    def test_correct_checkmark(self):  self.assertIn("✅", feedback_html(True, "stand","stand"))
    def test_wrong_cross(self):        self.assertIn("❌", feedback_html(False,"hit","stand"))
    def test_wrong_shows_optimal(self):self.assertIn("Stand", feedback_html(False,"hit","stand"))
    def test_returns_string(self):     self.assertIsInstance(feedback_html(True,"hit","hit"), str)


class TestSimulationLogic(unittest.TestCase):

    def test_run_returns_structure(self):
        from ml.simulation import run_all_simulations
        r = run_all_simulations(100, 1, 10)
        for key in ("basic", "player", "random"):
            self.assertIn(key, r)

    def test_required_fields(self):
        from ml.simulation import run_all_simulations
        r = run_all_simulations(100, 1, 10)
        for key in ("basic", "player", "random"):
            for field in ("balance","win_rate","ev_per_round","balance_history","counts"):
                self.assertIn(field, r[key])

    def test_win_rate_in_range(self):
        from ml.simulation import run_all_simulations
        r = run_all_simulations(200, 1, 10)
        for key in ("basic","player","random"):
            wr = r[key]["win_rate"]
            self.assertGreaterEqual(wr, 0.0)
            self.assertLessEqual(wr, 1.0)

    def test_history_not_empty(self):
        from ml.simulation import run_all_simulations
        r = run_all_simulations(200, 1, 10)
        for key in ("basic","player","random"):
            self.assertGreater(len(r[key]["balance_history"]), 0)

    def test_counts_sum_to_n(self):
        from ml.simulation import run_all_simulations
        n = 150
        r = run_all_simulations(n, 1, 10)
        for key in ("basic","player","random"):
            self.assertEqual(sum(r[key]["counts"].values()), n)

    def test_n_rounds_stored(self):
        from ml.simulation import run_all_simulations
        r = run_all_simulations(100, 1, 10)
        self.assertEqual(r["n_rounds"], 100)

    def test_basic_better_than_random(self):
        """Basic strategy должна давать лучший EV чем random (3 прогона)."""
        from ml.simulation import run_all_simulations
        basic_evs, random_evs = [], []
        for _ in range(3):
            r = run_all_simulations(500, 1, 10)
            basic_evs.append(r["basic"]["ev_per_round"])
            random_evs.append(r["random"]["ev_per_round"])
        avg_basic  = sum(basic_evs)  / 3
        avg_random = sum(random_evs) / 3
        self.assertGreater(avg_basic, avg_random)

    def test_simulate_strategy_directly(self):
        from ml.simulation import simulate_strategy, _basic_strategy
        r = simulate_strategy(_basic_strategy, 100, 1, 10)
        self.assertIsInstance(r["balance"], float)
        self.assertEqual(sum(r["counts"].values()), 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
