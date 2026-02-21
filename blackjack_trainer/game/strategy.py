from game.engine import Action
from typing import Dict, Tuple

# Dealer upcard index order: 2,3,4,5,6,7,8,9,10,Ace
DEALER_UPCARDS = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11]

H  = Action.HIT
S  = Action.STAND
D  = Action.DOUBLE
P  = Action.SPLIT
Ds = Action.DOUBLE  # Double if allowed, else Stand

# Hard hands (player total → action per dealer upcard 2..A)
HARD: Dict[int, list] = {
    #        2  3  4  5  6  7  8  9  10  A
    8:  [H, H, H, H, H, H, H, H,  H, H],
    9:  [H, D, D, D, D, H, H, H,  H, H],
    10: [D, D, D, D, D, D, D, D,  H, H],
    11: [D, D, D, D, D, D, D, D,  D, H],
    12: [H, H, S, S, S, H, H, H,  H, H],
    13: [S, S, S, S, S, H, H, H,  H, H],
    14: [S, S, S, S, S, H, H, H,  H, H],
    15: [S, S, S, S, S, H, H, H,  H, H],
    16: [S, S, S, S, S, H, H, H,  H, H],
    17: [S, S, S, S, S, S, S, S,  S, S],
}

# Soft hands (total with ace as 11)
SOFT: Dict[int, list] = {
    #        2  3  4  5  6  7  8  9  10  A
    13: [H, H, H, D, D, H, H, H,  H, H],   # A+2
    14: [H, H, H, D, D, H, H, H,  H, H],   # A+3
    15: [H, H, D, D, D, H, H, H,  H, H],   # A+4
    16: [H, H, D, D, D, H, H, H,  H, H],   # A+5
    17: [H, D, D, D, D, H, H, H,  H, H],   # A+6
    18: [Ds,Ds,Ds,Ds,Ds,S, S, H,  H, H],   # A+7
    19: [S, S, S, S, S, S, S, S,  S, S],   # A+8
    20: [S, S, S, S, S, S, S, S,  S, S],   # A+9
}

# Pairs (pair card value → action per dealer upcard 2..A)
PAIRS: Dict[int, list] = {
    #        2  3  4  5  6  7  8  9  10  A
    2:  [P, P, P, P, P, P, H, H,  H, H],
    3:  [P, P, P, P, P, P, H, H,  H, H],
    4:  [H, H, H, P, P, H, H, H,  H, H],
    5:  [D, D, D, D, D, D, D, D,  H, H],  # pair of 5s = hard 10
    6:  [P, P, P, P, P, H, H, H,  H, H],
    7:  [P, P, P, P, P, P, H, H,  H, H],
    8:  [P, P, P, P, P, P, P, P,  P, P],  # always split
    9:  [P, P, P, P, P, S, P, P,  S, S],
    10: [S, S, S, S, S, S, S, S,  S, S],  # never split tens
    11: [P, P, P, P, P, P, P, P,  P, P],  # always split aces
}


def _dealer_idx(dealer_upcard: int) -> int:
    if dealer_upcard not in DEALER_UPCARDS:
        raise ValueError(f"Invalid dealer upcard: {dealer_upcard}. Expected 2–11")
    return DEALER_UPCARDS.index(dealer_upcard)


def get_optimal_action(
    player_total: int,
    dealer_upcard: int,
    is_soft: bool,
    is_pair: bool,
    pair_card_value: int = 0,
) -> Action:
    """Return the basic strategy optimal action for this situation."""
    d_idx = _dealer_idx(dealer_upcard)

    if is_pair and pair_card_value in PAIRS:
        return PAIRS[pair_card_value][d_idx]

    if is_soft and player_total in SOFT:
        return SOFT[player_total][d_idx]

    if player_total <= 8:
        return Action.HIT
    if player_total >= 18:
        return Action.STAND

    if player_total in HARD:
        return HARD[player_total][d_idx]

    return Action.STAND


def evaluate_action(
    action: Action,
    player_total: int,
    dealer_upcard: int,
    is_soft: bool,
    is_pair: bool,
    pair_card_value: int = 0,
) -> Tuple[bool, Action]:
    """Compare player's action to the optimal one. Returns (is_correct, optimal)."""
    optimal = get_optimal_action(
        player_total=player_total,
        dealer_upcard=dealer_upcard,
        is_soft=is_soft,
        is_pair=is_pair,
        pair_card_value=pair_card_value,
    )
    return action == optimal, optimal
