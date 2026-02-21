"""
Тесты ML слоя: features, trainer, predictor, bootstrap.
Не требуют Streamlit.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import unittest
import tempfile
import numpy as np
from pathlib import Path

from ml.features import (
    moves_to_dataframe, get_feature_matrix,
    extract_features_single, compute_cluster_features,
    FEATURE_NAMES,
)
from ml.bootstrap import generate_synthetic_moves
from ml.trainer import MLTrainer, CLUSTER_NAMES, MIN_MOVES_RF


# ─── helpers ──────────────────────────────────────────────────────────────────

def make_moves(n=100, error_rate=0.35):
    return generate_synthetic_moves(n, error_rate)


def make_trainer(moves, tmpdir):
    """Создаёт MLTrainer с временной директорией для моделей."""
    import ml.trainer as _t
    orig = _t.MODELS_DIR
    _t.MODELS_DIR = Path(tmpdir)
    t = MLTrainer(player_id=1)
    t.train(moves)
    _t.MODELS_DIR = orig
    return t


# ══════════════════════════════════════════════════════════════════════════════
#  BOOTSTRAP
# ══════════════════════════════════════════════════════════════════════════════

class TestBootstrap(unittest.TestCase):

    def test_returns_correct_count(self):
        moves = generate_synthetic_moves(100)
        self.assertEqual(len(moves), 100)

    def test_required_keys(self):
        m = generate_synthetic_moves(10)[0]
        for key in ("player_total","dealer_upcard_val","is_soft","is_pair",
                    "action_taken","optimal_action","is_correct"):
            self.assertIn(key, m)

    def test_error_rate_approximate(self):
        moves = generate_synthetic_moves(500, error_rate=0.3)
        errors = sum(1 for m in moves if not m["is_correct"])
        rate = errors / len(moves)
        # Погрешность ±15%
        self.assertGreater(rate, 0.10)
        self.assertLess(rate, 0.55)

    def test_all_correct_zero_error(self):
        moves = generate_synthetic_moves(200, error_rate=0.0)
        errors = sum(1 for m in moves if not m["is_correct"])
        self.assertEqual(errors, 0)

    def test_player_total_in_range(self):
        for m in generate_synthetic_moves(200):
            self.assertGreaterEqual(m["player_total"], 2)
            self.assertLessEqual(m["player_total"], 21)

    def test_dealer_upcard_in_range(self):
        for m in generate_synthetic_moves(200):
            self.assertGreaterEqual(m["dealer_upcard_val"], 2)
            self.assertLessEqual(m["dealer_upcard_val"], 11)

    def test_actions_are_valid(self):
        valid = {"hit","stand","double","split"}
        for m in generate_synthetic_moves(200):
            self.assertIn(m["action_taken"], valid)


# ══════════════════════════════════════════════════════════════════════════════
#  FEATURE ENGINEERING
# ══════════════════════════════════════════════════════════════════════════════

class TestFeatureEngineering(unittest.TestCase):

    def setUp(self):
        self.moves = make_moves(100)

    def test_dataframe_shape(self):
        df = moves_to_dataframe(self.moves)
        self.assertEqual(len(df), 100)

    def test_all_feature_columns_present(self):
        df = moves_to_dataframe(self.moves)
        for feat in FEATURE_NAMES:
            self.assertIn(feat, df.columns)

    def test_player_total_norm_range(self):
        df = moves_to_dataframe(self.moves)
        self.assertTrue((df["player_total_norm"] >= 0).all())
        self.assertTrue((df["player_total_norm"] <= 1).all())

    def test_dealer_upcard_norm_range(self):
        df = moves_to_dataframe(self.moves)
        self.assertTrue((df["dealer_upcard_norm"] >= 0).all())
        self.assertTrue((df["dealer_upcard_norm"] <= 1.01).all())

    def test_binary_features_are_0_or_1(self):
        df = moves_to_dataframe(self.moves)
        for col in ["is_soft","is_pair","action_hit","action_stand","action_double","action_split"]:
            vals = df[col].unique()
            self.assertTrue(set(vals).issubset({0, 1}), f"{col}: {vals}")

    def test_is_correct_column_present(self):
        df = moves_to_dataframe(self.moves)
        self.assertIn("is_correct", df.columns)

    def test_empty_moves_returns_empty_df(self):
        df = moves_to_dataframe([])
        self.assertTrue(df.empty)

    def test_get_feature_matrix_shape(self):
        X, y = get_feature_matrix(self.moves)
        self.assertEqual(X.shape[0], len(self.moves))
        self.assertEqual(X.shape[1], len(FEATURE_NAMES))
        self.assertEqual(len(y), len(self.moves))

    def test_get_feature_matrix_empty(self):
        X, y = get_feature_matrix([])
        self.assertEqual(X.shape[0], 0)
        self.assertEqual(len(y), 0)

    def test_extract_single_shape(self):
        move = self.moves[0]
        X = extract_features_single(move)
        self.assertEqual(X.shape, (1, len(FEATURE_NAMES)))

    def test_extract_single_type(self):
        X = extract_features_single(self.moves[0])
        self.assertEqual(X.dtype, np.float32)

    def test_compute_cluster_features_shape(self):
        feat = compute_cluster_features(self.moves)
        self.assertIsNotNone(feat)
        self.assertEqual(feat.shape[1], 9)   # CLUSTER_FEATURE_NAMES count

    def test_compute_cluster_features_too_few(self):
        feat = compute_cluster_features(make_moves(5))
        self.assertIsNone(feat)

    def test_is_risky_flag(self):
        """is_risky = 1 для рук 15-16 vs дилер 7+."""
        risky_move = {
            "player_total": 16, "dealer_upcard_val": 10,
            "is_soft": 0, "is_pair": 0, "pair_card_value": 0,
            "action_taken": "stand",
        }
        df = moves_to_dataframe([risky_move])
        self.assertEqual(df["is_risky"].iloc[0], 1)

    def test_not_risky_for_safe_hand(self):
        safe_move = {
            "player_total": 17, "dealer_upcard_val": 6,
            "is_soft": 0, "is_pair": 0, "pair_card_value": 0,
            "action_taken": "stand",
        }
        df = moves_to_dataframe([safe_move])
        self.assertEqual(df["is_risky"].iloc[0], 0)


# ══════════════════════════════════════════════════════════════════════════════
#  TRAINER
# ══════════════════════════════════════════════════════════════════════════════

class TestMLTrainer(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.moves  = make_moves(150, error_rate=0.35)

    def _make_trainer(self, moves=None):
        import ml.trainer as _t
        orig = _t.MODELS_DIR
        _t.MODELS_DIR = Path(self.tmpdir)
        t = MLTrainer(player_id=999)
        if moves is not None:
            t.train(moves or self.moves)
        _t.MODELS_DIR = orig
        return t

    def test_not_trained_initially(self):
        t = self._make_trainer()
        self.assertFalse(t.is_trained)

    def test_train_sets_is_trained(self):
        t = self._make_trainer(self.moves)
        self.assertTrue(t.is_trained)

    def test_train_returns_dict(self):
        import ml.trainer as _t
        orig = _t.MODELS_DIR
        _t.MODELS_DIR = Path(self.tmpdir)
        t = MLTrainer(player_id=998)
        result = t.train(self.moves)
        _t.MODELS_DIR = orig
        self.assertIsInstance(result, dict)

    def test_rf_model_created(self):
        t = self._make_trainer(self.moves)
        self.assertIsNotNone(t._rf)

    def test_km_model_created(self):
        t = self._make_trainer(self.moves)
        self.assertIsNotNone(t._km)

    def test_rf_can_predict(self):
        t = self._make_trainer(self.moves)
        X = extract_features_single(self.moves[0])
        proba = t._rf.predict_proba(X)
        self.assertEqual(proba.shape[0], 1)
        self.assertAlmostEqual(proba[0].sum(), 1.0, places=3)

    def test_needs_retrain_when_untrained(self):
        t = self._make_trainer()
        self.assertTrue(t.needs_retrain(MIN_MOVES_RF))

    def test_no_retrain_right_after_training(self):
        t = self._make_trainer(self.moves)
        self.assertFalse(t.needs_retrain(len(self.moves)))

    def test_needs_retrain_after_25_new_moves(self):
        t = self._make_trainer(self.moves)
        self.assertTrue(t.needs_retrain(len(self.moves) + 26))

    def test_save_load_roundtrip(self):
        """Обученная модель сохраняется и загружается корректно."""
        import ml.trainer as _t
        orig = _t.MODELS_DIR
        _t.MODELS_DIR = Path(self.tmpdir)

        t1 = MLTrainer(player_id=777)
        t1.train(self.moves)

        t2 = MLTrainer(player_id=777)   # загружается из файла
        _t.MODELS_DIR = orig

        self.assertTrue(t2.is_trained)
        self.assertEqual(t2.n_moves_trained, len(self.moves))

    def test_too_few_moves_skips_rf(self):
        t = self._make_trainer(make_moves(10))
        # С 10 ходами RF не обучается
        self.assertFalse(t.is_trained)

    def test_cluster_names_coverage(self):
        for i in range(4):
            self.assertIn(i, CLUSTER_NAMES)


# ══════════════════════════════════════════════════════════════════════════════
#  PREDICTOR
# ══════════════════════════════════════════════════════════════════════════════

class TestMLPredictor(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.moves  = make_moves(150, error_rate=0.4)
        import ml.trainer as _t
        orig = _t.MODELS_DIR
        _t.MODELS_DIR = Path(self.tmpdir)
        self.trainer = MLTrainer(player_id=555)
        self.trainer.train(self.moves)
        _t.MODELS_DIR = orig
        from ml.predictor import MLPredictor
        self.predictor = MLPredictor(self.trainer)

    def test_error_prob_returns_float(self):
        prob = self.predictor.error_probability(16, 10, False, False, 0, "stand")
        self.assertIsNotNone(prob)
        self.assertIsInstance(prob, float)

    def test_error_prob_in_range(self):
        prob = self.predictor.error_probability(16, 10, False, False, 0, "stand")
        self.assertGreaterEqual(prob, 0.0)
        self.assertLessEqual(prob, 1.0)

    def test_untrained_returns_none(self):
        import ml.trainer as _t
        orig = _t.MODELS_DIR
        _t.MODELS_DIR = Path(self.tmpdir)
        untrained = MLTrainer(player_id=666)  # не обучен
        _t.MODELS_DIR = orig
        from ml.predictor import MLPredictor
        p = MLPredictor(untrained)
        self.assertIsNone(p.error_probability(16, 10, False, False, 0))

    def test_should_warn_high_prob(self):
        self.assertTrue(self.predictor.should_warn(0.75))

    def test_should_not_warn_low_prob(self):
        self.assertFalse(self.predictor.should_warn(0.3))

    def test_should_not_warn_none(self):
        self.assertFalse(self.predictor.should_warn(None))

    def test_warning_message_not_empty_when_high(self):
        msg = self.predictor.get_warning_message(0.75)
        self.assertGreater(len(msg), 0)

    def test_warning_message_empty_when_low(self):
        msg = self.predictor.get_warning_message(0.3)
        self.assertEqual(msg, "")

    def test_top_mistakes_returns_list(self):
        result = self.predictor.top_mistakes(self.moves, n=3)
        self.assertIsInstance(result, list)
        self.assertLessEqual(len(result), 3)

    def test_top_mistakes_has_required_fields(self):
        result = self.predictor.top_mistakes(self.moves)
        for item in result:
            self.assertIn("player_total",  item)
            self.assertIn("dealer_upcard", item)
            self.assertIn("error_prob",    item)

    def test_top_mistakes_error_prob_sorted(self):
        result = self.predictor.top_mistakes(self.moves, n=5)
        if len(result) > 1:
            probs = [r["error_prob"] for r in result]
            self.assertEqual(probs, sorted(probs, reverse=True))

    def test_get_cluster_info_returns_dict(self):
        info = self.predictor.get_cluster_info(self.moves)
        if info is not None:
            self.assertIn("cluster_id",   info)
            self.assertIn("cluster_name", info)
            self.assertIn(info["cluster_id"], range(4))


if __name__ == "__main__":
    unittest.main(verbosity=2)


# ══════════════════════════════════════════════════════════════════════════════
#  INTEGRATION — GameSession + ML
# ══════════════════════════════════════════════════════════════════════════════

class TestGameSessionML(unittest.TestCase):
    """Проверяем ML-методы GameSession."""

    def setUp(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from data.database import Database
        from data.game_session import GameSession
        from game.engine import Action

        self.db = Database(":memory:")
        self.gs = GameSession(db=self.db)
        self.Action = Action

        # Разыгрываем 60 раундов чтобы обучить ML
        for _ in range(60):
            self.gs.new_round()
            while self.gs.round_active:
                try:
                    self.gs.act(Action.STAND)
                except Exception:
                    break
            if not self.gs.round_active:
                self.gs.finish_round()

    def test_trainer_trained_after_60_rounds(self):
        self.assertTrue(self.gs._trainer.is_trained)

    def test_ml_warning_returns_str_or_none(self):
        self.gs.new_round()
        w = self.gs.ml_warning()
        self.assertIn(type(w), [str, type(None)])

    def test_ml_cluster_returns_dict_or_none(self):
        result = self.gs.ml_cluster()
        if result is not None:
            self.assertIn("cluster_id",   result)
            self.assertIn("cluster_name", result)
            self.assertIn(result["cluster_id"], range(4))

    def test_ml_top_mistakes_returns_list(self):
        result = self.gs.ml_top_mistakes(3)
        self.assertIsInstance(result, list)
        self.assertLessEqual(len(result), 3)

    def test_ml_top_mistakes_sorted_by_prob(self):
        result = self.gs.ml_top_mistakes(5)
        if len(result) > 1:
            probs = [r["error_prob"] for r in result]
            self.assertEqual(probs, sorted(probs, reverse=True))

    def test_ml_retrain_triggers_after_25_new_moves(self):
        n_before = self.gs._trainer.n_moves_trained
        # Play enough rounds to cross the retrain threshold (n_before + 25 real moves)
        for _ in range(50):
            self.gs.new_round()
            while self.gs.round_active:
                try:
                    self.gs.act(self.Action.STAND)
                except Exception:
                    break
            if not self.gs.round_active:
                self.gs.finish_round()
        n_after = self.gs._trainer.n_moves_trained
        self.assertGreater(n_after, n_before)
