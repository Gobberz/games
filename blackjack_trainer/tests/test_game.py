"""
Тесты для game/engine.py и game/strategy.py
Запуск: python -m unittest discover -s tests -v
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import unittest
from game.engine import Card, Deck, Hand, Game, Action, GameResult, Suit
from game.strategy import get_optimal_action, evaluate_action


def make_hand(*ranks):
    return Hand([Card(Suit.SPADES, r) for r in ranks])


class TestCard(unittest.TestCase):
    def test_numeric_value(self):       self.assertEqual(Card(Suit.SPADES, "7").value, 7)
    def test_face_j(self):              self.assertEqual(Card(Suit.HEARTS, "J").value, 10)
    def test_face_q(self):              self.assertEqual(Card(Suit.HEARTS, "Q").value, 10)
    def test_face_k(self):              self.assertEqual(Card(Suit.HEARTS, "K").value, 10)
    def test_ace_value(self):           self.assertEqual(Card(Suit.DIAMONDS, "A").value, 11)
    def test_ten_value(self):           self.assertEqual(Card(Suit.CLUBS, "10").value, 10)
    def test_display_has_suit(self):    self.assertIn("♠", Card(Suit.SPADES, "A").display)
    def test_invalid_rank(self):
        with self.assertRaises(ValueError): Card(Suit.SPADES, "1")
    def test_invalid_zero(self):
        with self.assertRaises(ValueError): Card(Suit.SPADES, "0")
    def test_immutable(self):
        c = Card(Suit.SPADES, "A")
        with self.assertRaises((AttributeError, TypeError)): c.rank = "K"  # type: ignore


class TestDeck(unittest.TestCase):
    def test_single_deck_52(self):      self.assertEqual(len(Deck(1)), 52)
    def test_six_decks_312(self):       self.assertEqual(len(Deck(6)), 312)
    def test_deal_reduces_count(self):
        d = Deck(1); before = len(d); d.deal()
        self.assertEqual(len(d), before - 1)
    def test_deal_returns_card(self):   self.assertIsInstance(Deck(1).deal(), Card)
    def test_zero_decks_raises(self):
        with self.assertRaises(ValueError): Deck(0)
    def test_reshuffle_on_low(self):
        d = Deck(1)
        for _ in range(49): d.deal()
        d.deal()  # triggers reshuffle
        self.assertGreater(len(d), 40)
    def test_all_ranks(self):
        ranks = {c.rank for c in Deck(1)._cards}
        self.assertEqual(ranks, {str(i) for i in range(2,11)} | {"J","Q","K","A"})
    def test_all_suits(self):
        self.assertEqual({c.suit for c in Deck(1)._cards}, set(Suit))


class TestHandValue(unittest.TestCase):
    def test_simple_sum(self):           self.assertEqual(make_hand("7","8").value, 15)
    def test_ace_as_11(self):            self.assertEqual(make_hand("A","9").value, 20)
    def test_ace_drops_to_1(self):       self.assertEqual(make_hand("A","9","5").value, 15)
    def test_two_aces(self):             self.assertEqual(make_hand("A","A").value, 12)
    def test_two_aces_nine_21(self):     self.assertEqual(make_hand("A","A","9").value, 21)
    def test_blackjack_ak(self):
        h = make_hand("A","K"); self.assertEqual(h.value, 21); self.assertTrue(h.is_blackjack)
    def test_blackjack_a10(self):        self.assertTrue(make_hand("A","10").is_blackjack)
    def test_three_sevens_not_bj(self):  self.assertFalse(make_hand("7","7","7").is_blackjack)
    def test_bust(self):
        h = make_hand("K","Q","5"); self.assertTrue(h.is_bust); self.assertEqual(h.value, 25)
    def test_21_not_bust(self):          self.assertFalse(make_hand("7","7","7").is_bust)
    def test_soft_17(self):
        h = make_hand("A","6"); self.assertEqual(h.value, 17); self.assertTrue(h.is_soft)
    def test_hard_17(self):
        h = make_hand("10","7"); self.assertFalse(h.is_soft)
    def test_soft_becomes_hard(self):
        h = make_hand("A","6","10"); self.assertEqual(h.value, 17); self.assertFalse(h.is_soft)
    def test_face_sum_20(self):          self.assertEqual(make_hand("K","Q").value, 20)


class TestHandPair(unittest.TestCase):
    def test_pair_eights(self):         self.assertTrue(make_hand("8","8").is_pair)
    def test_pair_aces(self):           self.assertTrue(make_hand("A","A").is_pair)
    def test_diff_suits_pair(self):
        self.assertTrue(Hand([Card(Suit.SPADES,"8"), Card(Suit.HEARTS,"8")]).is_pair)
    def test_ten_king_value_pair(self):
        self.assertTrue(Hand([Card(Suit.SPADES,"10"), Card(Suit.HEARTS,"K")]).is_pair)
    def test_three_cards_not_pair(self): self.assertFalse(make_hand("8","8","8").is_pair)
    def test_diff_values_not_pair(self): self.assertFalse(make_hand("8","9").is_pair)
    def test_split_two_hands(self):
        h1, h2 = make_hand("8","8").split()
        self.assertEqual(len(h1), 1); self.assertEqual(len(h2), 1)
    def test_split_non_pair_raises(self):
        with self.assertRaises(ValueError): make_hand("8","9").split()
    def test_can_double_2cards(self):   self.assertTrue(make_hand("5","6").can_double)
    def test_no_double_3cards(self):    self.assertFalse(make_hand("5","6","2").can_double)


class TestGame(unittest.TestCase):
    def test_new_round_2_cards(self):
        g = Game(); g.new_round()
        self.assertEqual(len(g.player_hand), 2); self.assertEqual(len(g.dealer_hand), 2)
    def test_dealer_upcard_exists(self):
        g = Game(); g.new_round(); self.assertIsInstance(g.dealer_upcard, Card)
    def test_stand_ends_round(self):
        g = Game(); g.new_round(); g.player_action(Action.STAND); self.assertFalse(g.round_active)
    def test_double_one_card(self):
        g = Game(); g.new_round()
        while g.player_hand.value not in (9,10,11): g.new_round()
        before = len(g.player_hand); g.player_action(Action.DOUBLE)
        self.assertEqual(len(g.player_hand), before + 1)
    def test_double_ends_round(self):
        g = Game(); g.new_round()
        while g.player_hand.value not in (9,10,11): g.new_round()
        g.player_action(Action.DOUBLE); self.assertFalse(g.round_active)
    def test_action_before_round_raises(self):
        with self.assertRaises(RuntimeError): Game().player_action(Action.HIT)
    def test_split_creates_two_hands(self):
        g = Game(); g.new_round()
        while not g.player_hand.is_pair: g.new_round()
        g.player_action(Action.SPLIT); self.assertEqual(len(g._split_hands), 2)
    def test_dealer_ge_17_after_play(self):
        g = Game(); g.new_round(); g.player_action(Action.STAND); g.dealer_play()
        self.assertGreaterEqual(g.dealer_hand.value, 17)

    def _game(self, p_ranks, d_ranks):
        g = Game(); g.new_round()
        g.player_hand = Hand([Card(Suit.SPADES, r) for r in p_ranks])
        g.dealer_hand = Hand([Card(Suit.HEARTS, r) for r in d_ranks])
        g._round_active = False; return g

    def test_eval_win(self):    self.assertEqual(self._game(["10","9"],["7","8"])._evaluate(self._game(["10","9"],["7","8"]).player_hand), GameResult.WIN)
    def test_eval_lose(self):   self.assertEqual(self._game(["10","5"],["10","8"])._evaluate(self._game(["10","5"],["10","8"]).player_hand), GameResult.LOSE)
    def test_eval_push(self):   self.assertEqual(self._game(["10","8"],["9","9"])._evaluate(self._game(["10","8"],["9","9"]).player_hand), GameResult.PUSH)
    def test_eval_bj(self):     self.assertEqual(self._game(["A","K"],["7","7","7"])._evaluate(self._game(["A","K"],["7","7","7"]).player_hand), GameResult.BLACKJACK)
    def test_eval_dealer_bust(self): self.assertEqual(self._game(["10","6"],["K","Q","5"])._evaluate(self._game(["10","6"],["K","Q","5"]).player_hand), GameResult.WIN)
    def test_eval_both_bj_push(self): self.assertEqual(self._game(["A","K"],["A","Q"])._evaluate(self._game(["A","K"],["A","Q"]).player_hand), GameResult.PUSH)
    def test_eval_player_bust(self):  self.assertEqual(self._game(["K","Q","5"],["7","8"])._evaluate(self._game(["K","Q","5"],["7","8"]).player_hand), GameResult.BUST)


class TestStrategy(unittest.TestCase):
    def _opt(self, t, d, s=False, p=False, pv=0):
        return get_optimal_action(t, d, s, p, pv)

    # Hard
    def test_hard8_all_hit(self):
        for d in range(2,12):
            with self.subTest(d=d): self.assertEqual(self._opt(8,d), Action.HIT)
    def test_hard17_all_stand(self):
        for d in range(2,12):
            with self.subTest(d=d): self.assertEqual(self._opt(17,d), Action.STAND)
    def test_hard18to21_stand(self):
        for t in (18,19,20,21):
            for d in range(2,12):
                with self.subTest(t=t,d=d): self.assertEqual(self._opt(t,d), Action.STAND)
    def test_hard11_double_vs6(self):   self.assertEqual(self._opt(11,6), Action.DOUBLE)
    def test_hard11_double_vs10(self):  self.assertEqual(self._opt(11,10), Action.DOUBLE)
    def test_hard11_hit_vsAce(self):    self.assertEqual(self._opt(11,11), Action.HIT)
    def test_hard12_hit_vs2(self):      self.assertEqual(self._opt(12,2), Action.HIT)
    def test_hard12_stand_vs4(self):    self.assertEqual(self._opt(12,4), Action.STAND)
    def test_hard16_stand_vs6(self):    self.assertEqual(self._opt(16,6), Action.STAND)
    def test_hard16_hit_vs7(self):      self.assertEqual(self._opt(16,7), Action.HIT)
    # Soft
    def test_soft17_hit_vs2(self):      self.assertEqual(self._opt(17,2,s=True), Action.HIT)
    def test_soft17_dbl_vs3(self):      self.assertEqual(self._opt(17,3,s=True), Action.DOUBLE)
    def test_soft18_stand_vs7(self):    self.assertEqual(self._opt(18,7,s=True), Action.STAND)
    def test_soft18_hit_vs9(self):      self.assertEqual(self._opt(18,9,s=True), Action.HIT)
    def test_soft19_all_stand(self):
        for d in range(2,12):
            with self.subTest(d=d): self.assertEqual(self._opt(19,d,s=True), Action.STAND)
    # Pairs
    def test_aces_always_split(self):
        for d in range(2,12):
            with self.subTest(d=d): self.assertEqual(self._opt(12,d,p=True,pv=11), Action.SPLIT)
    def test_eights_always_split(self):
        for d in range(2,12):
            with self.subTest(d=d): self.assertEqual(self._opt(16,d,p=True,pv=8), Action.SPLIT)
    def test_tens_no_split(self):
        for d in range(2,12):
            with self.subTest(d=d): self.assertEqual(self._opt(20,d,p=True,pv=10), Action.STAND)
    def test_fives_as_hard10(self):     self.assertEqual(self._opt(10,6,p=True,pv=5), Action.DOUBLE)
    def test_fours_split_vs5(self):     self.assertEqual(self._opt(8,5,p=True,pv=4), Action.SPLIT)
    def test_fours_hit_vs2(self):       self.assertEqual(self._opt(8,2,p=True,pv=4), Action.HIT)
    def test_nines_split_vs9(self):     self.assertEqual(self._opt(18,9,p=True,pv=9), Action.SPLIT)
    def test_nines_stand_vs7(self):     self.assertEqual(self._opt(18,7,p=True,pv=9), Action.STAND)
    # evaluate
    def test_correct_stand17(self):
        ok, opt = evaluate_action(Action.STAND, 17, 10, False, False)
        self.assertTrue(ok); self.assertEqual(opt, Action.STAND)
    def test_wrong_hit17(self):
        ok, opt = evaluate_action(Action.HIT, 17, 10, False, False)
        self.assertFalse(ok); self.assertEqual(opt, Action.STAND)
    def test_correct_dbl_soft18_vs3(self):
        ok, _ = evaluate_action(Action.DOUBLE, 18, 3, True, False); self.assertTrue(ok)
    def test_correct_split_aces(self):
        ok, _ = evaluate_action(Action.SPLIT, 12, 7, False, True, pair_card_value=11)
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main(verbosity=2)
