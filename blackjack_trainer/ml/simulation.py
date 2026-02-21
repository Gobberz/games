import random
from game.engine import Game, Action, GameResult
from game.strategy import get_optimal_action


def _basic_strategy(total, dealer, soft, pair, pv, can_double, can_split):
    action = get_optimal_action(total, dealer, soft, pair, pv)
    if action == Action.SPLIT:
        return Action.SPLIT if can_split else Action.HIT
    if action == Action.DOUBLE:
        return Action.DOUBLE if can_double else Action.HIT
    return action


def _random_strategy(total, dealer, soft, pair, pv, can_double, can_split):
    return random.choice([Action.HIT, Action.STAND])


def _player_strategy(total, dealer, soft, pair, pv, can_double, can_split):
    """Simple beginner heuristic: stand on 13+ vs weak dealer, double on 11."""
    if total >= 17:
        return Action.STAND
    if total >= 13 and dealer <= 6:
        return Action.STAND
    if total == 11 and can_double:
        return Action.DOUBLE
    return Action.HIT


def simulate_strategy(strategy_fn, n: int, num_decks: int, bet: float) -> dict:
    game    = Game(num_decks)
    balance = 0.0
    counts  = {"win": 0, "lose": 0, "push": 0, "blackjack": 0, "bust": 0}
    history = []

    for _ in range(n):
        game.new_round()

        for _ in range(10):  # cap hits to avoid infinite loops
            if not game.round_active:
                break
            ch         = game._active_hand
            dealer_val = game.dealer_upcard.value if game.dealer_upcard else 7
            action     = strategy_fn(
                ch.value, dealer_val, ch.is_soft, ch.is_pair,
                ch.cards[0].value if ch.is_pair else 0,
                can_double=ch.can_double,
                can_split=ch.can_split,
            )
            bust = game.player_action(action)
            if bust == GameResult.BUST:
                break

        if game.round_active:
            game.player_action(Action.STAND)

        result = game.dealer_play()
        rk     = result.value

        if rk in ("win", "blackjack"):
            pnl = bet * (1.5 if rk == "blackjack" else 1.0)
        elif rk in ("lose", "bust"):
            pnl = -bet
        else:
            pnl = 0.0

        balance += pnl
        counts[rk] = counts.get(rk, 0) + 1
        history.append(balance)

    total_rounds = sum(counts.values())
    wins = counts["win"] + counts["blackjack"]

    return {
        "balance":         balance,
        "win_rate":        wins / total_rounds if total_rounds else 0,
        "bust_rate":       counts["bust"] / total_rounds if total_rounds else 0,
        "balance_history": history[::max(1, n // 200)],
        "ev_per_round":    balance / n if n else 0,
        "counts":          counts,
    }


def run_all_simulations(n_rounds: int, num_decks: int, bet: float) -> dict:
    return {
        "basic":    simulate_strategy(_basic_strategy,  n_rounds, num_decks, bet),
        "player":   simulate_strategy(_player_strategy, n_rounds, num_decks, bet),
        "random":   simulate_strategy(_random_strategy, n_rounds, num_decks, bet),
        "n_rounds": n_rounds,
        "bet":      bet,
    }
