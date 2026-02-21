from __future__ import annotations
import random
from game.engine import Action
from game.strategy import get_optimal_action


def generate_synthetic_moves(n: int = 200, error_rate: float = 0.30) -> list[dict]:
    """
    Generates fake move records for cold-start ML training.
    Simulates a typical beginner: mostly correct but with common mistakes.
    """
    PLAYER_TOTALS = list(range(8, 18)) + list(range(12, 17)) * 2
    SOFT_TOTALS   = [13, 14, 15, 16, 17, 18, 19]
    PAIR_CARDS    = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    DEALER_CARDS  = list(range(2, 12))

    # Classic beginner mistakes
    COMMON_MISTAKES = [
        {"player_total": 16, "dealer_upcard_val": 10, "is_soft": 0, "is_pair": 0, "wrong_action": "stand"},
        {"player_total": 12, "dealer_upcard_val": 2,  "is_soft": 0, "is_pair": 0, "wrong_action": "stand"},
        {"player_total": 13, "dealer_upcard_val": 4,  "is_soft": 0, "is_pair": 0, "wrong_action": "hit"},
        {"player_total": 11, "dealer_upcard_val": 6,  "is_soft": 0, "is_pair": 0, "wrong_action": "stand"},
        {"player_total": 18, "dealer_upcard_val": 4,  "is_soft": 1, "is_pair": 0, "wrong_action": "hit"},
        {"player_total": 16, "dealer_upcard_val": 8,  "is_soft": 0, "is_pair": 1, "wrong_action": "hit", "pair_card_value": 8},
    ]

    moves = []
    for _ in range(n):
        is_mistake = random.random() < error_rate

        if is_mistake and random.random() < 0.6:
            m    = random.choice(COMMON_MISTAKES)
            pt   = m["player_total"]
            du   = m["dealer_upcard_val"]
            soft = m["is_soft"]
            pair = m["is_pair"]
            pcv  = m.get("pair_card_value", 0)
            action  = m["wrong_action"]
            optimal = get_optimal_action(pt, du, bool(soft), bool(pair), pcv)
            is_correct = (action == optimal.value)
        else:
            soft = random.random() < 0.25
            pair = random.random() < 0.10 and not soft

            if pair:
                pcv = random.choice(PAIR_CARDS)
                pt  = pcv * 2 if pcv < 11 else 12
            elif soft:
                pt  = random.choice(SOFT_TOTALS)
                pcv = 0
            else:
                pt  = random.choice(PLAYER_TOTALS)
                pcv = 0

            du      = random.choice(DEALER_CARDS)
            optimal = get_optimal_action(pt, du, soft, pair, pcv)

            if is_mistake:
                all_actions = ["hit", "stand", "double", "split"]
                wrong  = [a for a in all_actions if a != optimal.value]
                action = random.choice(wrong) if wrong else optimal.value
            else:
                action = optimal.value

            is_correct = (action == optimal.value)

        moves.append({
            "player_total":      pt,
            "dealer_upcard_val": du,
            "is_soft":           int(soft),
            "is_pair":           int(pair),
            "pair_card_value":   pcv,
            "action_taken":      action,
            "optimal_action":    optimal.value,
            "is_correct":        int(is_correct),
        })

    return moves
