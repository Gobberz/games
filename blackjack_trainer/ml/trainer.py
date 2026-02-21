from __future__ import annotations
import pickle
import time
from pathlib import Path
from typing import Optional

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score

from ml.features import (
    get_feature_matrix, compute_cluster_features,
    FEATURE_NAMES, CLUSTER_FEATURE_NAMES,
)

MODELS_DIR = Path(__file__).parent.parent / "models"
MODELS_DIR.mkdir(exist_ok=True)

MIN_MOVES_RF      = 50
MIN_MOVES_CLUSTER = 20
MIN_MOVES_LR      = 30

CLUSTER_NAMES = {0: "expert", 1: "cautious", 2: "impulsive", 3: "chaotic"}


class MLTrainer:
    """Manages training and persistence of all three models."""

    def __init__(self, player_id: int):
        self.player_id = player_id
        self._rf:     Optional[RandomForestClassifier] = None
        self._lr:     Optional[LogisticRegression]     = None
        self._km:     Optional[KMeans]                 = None
        self._scaler: Optional[StandardScaler]         = None
        self._trained_at:     float = 0.0
        self._n_moves_trained: int  = 0

        self._load()

    def _path(self, name: str) -> Path:
        return MODELS_DIR / f"player_{self.player_id}_{name}.pkl"

    def _save(self) -> None:
        bundle = {
            "rf": self._rf, "lr": self._lr, "km": self._km,
            "scaler": self._scaler,
            "trained_at": self._trained_at,
            "n_moves": self._n_moves_trained,
        }
        with open(self._path("bundle"), "wb") as f:
            pickle.dump(bundle, f)

    def _load(self) -> None:
        p = self._path("bundle")
        if p.exists():
            try:
                with open(p, "rb") as f:
                    bundle = pickle.load(f)
                self._rf     = bundle.get("rf")
                self._lr     = bundle.get("lr")
                self._km     = bundle.get("km")
                self._scaler = bundle.get("scaler")
                self._trained_at      = bundle.get("trained_at", 0.0)
                self._n_moves_trained = bundle.get("n_moves", 0)
            except Exception:
                pass  # corrupted file, we'll just retrain

    def train(self, moves: list[dict]) -> dict:
        results = {}

        if len(moves) >= MIN_MOVES_RF:
            results["rf"] = self._train_rf(moves)

        if len(moves) >= MIN_MOVES_CLUSTER:
            results["km"] = self._train_km(moves)

        if len(moves) >= MIN_MOVES_LR:
            results["lr"] = self._train_lr(moves)

        self._trained_at      = time.time()
        self._n_moves_trained = len(moves)
        self._save()

        return results

    def _train_rf(self, moves: list[dict]) -> dict:
        X, y = get_feature_matrix(moves)

        if len(np.unique(y)) < 2:
            return {"status": "skipped", "reason": "only_one_class"}

        self._rf = RandomForestClassifier(
            n_estimators=100,
            max_depth=6,
            min_samples_leaf=3,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )
        self._rf.fit(X, y)

        try:
            cv_scores = cross_val_score(self._rf, X, y, cv=min(3, len(y)//10 + 1), scoring="roc_auc")
            auc = float(cv_scores.mean())
        except Exception:
            auc = 0.0

        importance = dict(zip(FEATURE_NAMES, self._rf.feature_importances_.tolist()))
        return {"status": "trained", "n_samples": len(X), "roc_auc": round(auc, 3), "importance": importance}

    def _train_km(self, moves: list[dict]) -> dict:
        X, _ = get_feature_matrix(moves)
        if X.shape[0] < MIN_MOVES_CLUSTER:
            return {"status": "skipped", "reason": "too_few"}

        self._scaler = StandardScaler()
        X_scaled = self._scaler.fit_transform(X)

        self._km = KMeans(n_clusters=4, random_state=42, n_init=10)
        self._km.fit(X_scaled)

        cluster_feat = compute_cluster_features(moves)
        if cluster_feat is not None:
            player_mean = X_scaled.mean(axis=0).reshape(1, -1)
            cluster_id  = int(self._km.predict(player_mean)[0])
        else:
            cluster_id = 3

        return {"status": "trained", "cluster_id": cluster_id, "cluster_name": CLUSTER_NAMES.get(cluster_id, "unknown")}

    def _train_lr(self, moves: list[dict]) -> dict:
        X, y = get_feature_matrix(moves)
        if len(np.unique(y)) < 2:
            return {"status": "skipped", "reason": "only_one_class"}

        scaler   = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        self._lr = LogisticRegression(max_iter=500, class_weight="balanced", random_state=42, C=1.0)
        self._lr.fit(X_scaled, y)
        self._lr_scaler = scaler

        try:
            score = cross_val_score(self._lr, X_scaled, y, cv=min(3, len(y)//10 + 1)).mean()
        except Exception:
            score = 0.0

        return {"status": "trained", "accuracy": round(float(score), 3)}

    def needs_retrain(self, current_n_moves: int) -> bool:
        if self._rf is None:
            return current_n_moves >= MIN_MOVES_RF
        return current_n_moves >= self._n_moves_trained + 25

    @property
    def is_trained(self) -> bool:
        return self._rf is not None

    @property
    def n_moves_trained(self) -> int:
        return self._n_moves_trained
