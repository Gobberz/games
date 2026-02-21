from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Optional


FEATURE_NAMES = [
    "player_total_norm",
    "dealer_upcard_norm",
    "is_soft",
    "is_pair",
    "pair_card_norm",
    "is_risky",
    "dealer_strong",
    "dealer_weak",
    "player_low",
    "player_high",
    "action_hit",
    "action_stand",
    "action_double",
    "action_split",
]

CLUSTER_FEATURE_NAMES = [
    "hit_rate",
    "stand_rate",
    "double_rate",
    "split_rate",
    "soft_accuracy",
    "pair_accuracy",
    "avg_player_total_norm",
    "risky_hit_rate",
    "soft17_double_rate",
]


def moves_to_dataframe(moves: list[dict]) -> pd.DataFrame:
    if not moves:
        return pd.DataFrame()

    rows = []
    for m in moves:
        row = _extract_features(m)
        row["is_correct"] = int(m.get("is_correct", 0))
        rows.append(row)

    return pd.DataFrame(rows)


def _extract_features(move: dict) -> dict:
    pt  = int(move.get("player_total", 10))
    du  = int(move.get("dealer_upcard_val", 7))
    soft = int(move.get("is_soft", 0))
    pair = int(move.get("is_pair", 0))
    pcv  = int(move.get("pair_card_value", 0))
    act  = str(move.get("action_taken", "stand"))

    return {
        "player_total_norm":  pt / 21.0,
        "dealer_upcard_norm": du / 11.0,
        "pair_card_norm":     pcv / 11.0,
        "is_soft":   soft,
        "is_pair":   pair,
        # hands where players tend to mess up most
        "is_risky":      int(pt in (15, 16) and du >= 7),
        "dealer_strong": int(du >= 7),
        "dealer_weak":   int(2 <= du <= 6),
        "player_low":    int(pt <= 11),
        "player_high":   int(pt >= 17),
        "action_hit":    int(act == "hit"),
        "action_stand":  int(act == "stand"),
        "action_double": int(act == "double"),
        "action_split":  int(act == "split"),
    }


def get_feature_matrix(moves: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    df = moves_to_dataframe(moves)
    if df.empty:
        return np.empty((0, len(FEATURE_NAMES))), np.empty(0)

    X = df[FEATURE_NAMES].values.astype(np.float32)
    y = df["is_correct"].values.astype(np.int32)
    return X, y


def extract_features_single(move: dict) -> np.ndarray:
    features = _extract_features(move)
    return np.array([features[f] for f in FEATURE_NAMES], dtype=np.float32).reshape(1, -1)


def compute_cluster_features(moves: list[dict]) -> Optional[np.ndarray]:
    if len(moves) < 20:
        return None

    df = moves_to_dataframe(moves)

    hit_rate    = df["action_hit"].mean()
    stand_rate  = df["action_stand"].mean()
    double_rate = df["action_double"].mean()
    split_rate  = df["action_split"].mean()

    soft_mask = df["is_soft"] == 1
    soft_acc  = df.loc[soft_mask, "is_correct"].mean() if soft_mask.sum() > 0 else 0.5

    pair_mask = df["is_pair"] == 1
    pair_acc  = df.loc[pair_mask, "is_correct"].mean() if pair_mask.sum() > 0 else 0.5

    avg_total_norm = df["player_total_norm"].mean()

    risky_mask    = df["is_risky"] == 1
    risky_hit_rate = df.loc[risky_mask, "action_hit"].mean() if risky_mask.sum() > 0 else 0.5

    s17_mask = (df["is_soft"] == 1) & (df["player_total_norm"].round(2) == round(17/21, 2))
    soft17_dbl_rate = df.loc[s17_mask, "action_double"].mean() if s17_mask.sum() > 0 else 0.0

    features = np.array([
        hit_rate, stand_rate, double_rate, split_rate,
        soft_acc, pair_acc,
        avg_total_norm,
        risky_hit_rate,
        soft17_dbl_rate,
    ], dtype=np.float32)

    return features.reshape(1, -1)
