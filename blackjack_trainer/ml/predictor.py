from __future__ import annotations
from typing import Optional

import numpy as np
from ml.features import extract_features_single, FEATURE_NAMES
from ml.trainer import MLTrainer, CLUSTER_NAMES

WARNING_THRESHOLD = 0.60


class MLPredictor:
    """Real-time inference wrapper — predicts error probability before a move."""

    def __init__(self, trainer: MLTrainer):
        self.trainer = trainer

    def error_probability(
        self,
        player_total:      int,
        dealer_upcard_val: int,
        is_soft:           bool,
        is_pair:           bool,
        pair_card_value:   int,
        action_taken:      str = "stand",
    ) -> Optional[float]:
        """Returns P(mistake) for this situation, or None if not trained yet."""
        if not self.trainer.is_trained or self.trainer._rf is None:
            return None

        move = {
            "player_total":      player_total,
            "dealer_upcard_val": dealer_upcard_val,
            "is_soft":           int(is_soft),
            "is_pair":           int(is_pair),
            "pair_card_value":   pair_card_value,
            "action_taken":      action_taken,
        }

        X = extract_features_single(move)

        try:
            proba     = self.trainer._rf.predict_proba(X)
            classes   = self.trainer._rf.classes_
            wrong_idx = list(classes).index(0) if 0 in classes else 0
            return float(proba[0][wrong_idx])
        except Exception:
            return None

    def should_warn(self, error_prob: Optional[float]) -> bool:
        return error_prob is not None and error_prob >= WARNING_THRESHOLD

    def get_warning_message(self, error_prob: float) -> str:
        if error_prob < WARNING_THRESHOLD:
            return ""
        if error_prob >= 0.85:
            return f"⚠️ High error risk ({error_prob*100:.0f}%) — double check the strategy"
        return f"⚠️ You often make mistakes in this spot ({error_prob*100:.0f}%)"

    def get_cluster_info(self, moves: list[dict]) -> Optional[dict]:
        if self.trainer._km is None or self.trainer._scaler is None:
            return None

        from ml.features import get_feature_matrix
        X, _ = get_feature_matrix(moves)
        if X.shape[0] < 20:
            return None

        try:
            X_scaled   = self.trainer._scaler.transform(X)
            player_vec = X_scaled.mean(axis=0).reshape(1, -1)
            cluster_id = int(self.trainer._km.predict(player_vec)[0])
            return {"cluster_id": cluster_id, "cluster_name": CLUSTER_NAMES.get(cluster_id, "unknown")}
        except Exception:
            return None

    def top_mistakes(self, moves: list[dict], n: int = 5) -> list[dict]:
        """Top N situations by average error probability — used for personal tips."""
        if not self.trainer.is_trained:
            return []

        from ml.features import moves_to_dataframe
        import pandas as pd

        df = moves_to_dataframe(moves)
        if df.empty:
            return []

        X = df[FEATURE_NAMES].values.astype(np.float32)

        try:
            proba     = self.trainer._rf.predict_proba(X)
            classes   = self.trainer._rf.classes_
            wrong_idx = list(classes).index(0) if 0 in classes else 0
            error_probs = proba[:, wrong_idx]
        except Exception:
            return []

        df["error_prob"] = error_probs
        agg = (
            df.groupby(["player_total_norm", "dealer_upcard_norm", "is_soft"])["error_prob"]
            .mean()
            .reset_index()
            .sort_values("error_prob", ascending=False)
            .head(n)
        )

        results = []
        for _, row in agg.iterrows():
            results.append({
                "player_total":  round(row["player_total_norm"] * 21),
                "dealer_upcard": round(row["dealer_upcard_norm"] * 11),
                "is_soft":       bool(row["is_soft"]),
                "error_prob":    round(float(row["error_prob"]), 3),
            })
        return results
