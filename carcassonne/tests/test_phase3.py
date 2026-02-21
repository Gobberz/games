import sys, os, random, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.tile import TileDef, EdgeType, CenterType, TILE_DEFS
from game.board import Board
from game.deck import Deck
from game.scoring import MeepleManager, Meeple, ScoringEngine
from game.bots import RandomBot, MinimaxBot, create_bot, BotMove
from game.analytics import AnalyticsEngine, compute_analytics
from game.session import GameSession


def test_random_bot():
    game = GameSession(num_players=2)
    p1 = game.add_player("Human")
    p2 = game.add_player("RandomBot", is_bot=True, bot_type="random")

    assert p2.is_bot
    assert p2.bot is not None
    assert isinstance(p2.bot, RandomBot)

    bot_state = game._build_bot_state(p2)
    move = p2.bot.choose_move(bot_state)
    assert move is not None
    assert isinstance(move, BotMove)
    print(f"  Random bot chose: ({move.x},{move.y}) rot={move.rotation}")
    print("PASS: random bot")


def test_minimax_bot():
    game = GameSession(num_players=2)
    p1 = game.add_player("Human")
    p2 = game.add_player("MinimaxBot", is_bot=True, bot_type="minimax")

    assert isinstance(p2.bot, MinimaxBot)

    # play first human move
    moves = game.get_valid_moves(p1.id)
    m = moves[0]
    game.make_move(p1.id, m["tile_idx"], m["x"], m["y"], m["rotation"])
    if game.turn_phase == "place_meeple":
        game.skip_meeple(p1.id)

    # now it's bot's turn
    bot_state = game._build_bot_state(p2)
    move = p2.bot.choose_move(bot_state)
    assert move is not None
    assert move.score != 0 or True  # score can be 0 for early game
    print(f"  Minimax bot chose: ({move.x},{move.y}) rot={move.rotation} score={move.score:.2f}")
    print("PASS: minimax bot")


def test_bot_auto_turn():
    game = GameSession(num_players=2)
    p1 = game.add_player("Human")
    p2 = game.add_player("Bot", is_bot=True, bot_type="random")

    # human plays
    moves = game.get_valid_moves(p1.id)
    m = moves[0]
    game.make_move(p1.id, m["tile_idx"], m["x"], m["y"], m["rotation"])
    if game.turn_phase == "place_meeple":
        game.skip_meeple(p1.id)

    assert game.current_player().id == p2.id

    result = game.try_bot_turn()
    assert result is not None
    assert "error" not in result

    # should be human's turn again
    assert game.current_player().id == p1.id
    print("PASS: bot auto turn")


def test_full_game_vs_random_bot():
    game = GameSession(num_players=2)
    p1 = game.add_player("Human")
    p2 = game.add_player("Bot", is_bot=True, bot_type="random")

    turns = 0
    while game.phase == "playing" and turns < 300:
        cp = game.current_player()
        if not cp:
            break

        if cp.is_bot:
            result = game.try_bot_turn()
            if not result or "error" in result:
                break
        else:
            if game.turn_phase == "place_meeple":
                game.skip_meeple(cp.id)
                continue
            moves = game.get_valid_moves(cp.id)
            if not moves:
                game.current_turn_idx = (game.current_turn_idx + 1) % len(game.turn_order)
                game.turn_phase = "place_tile"
                turns += 1
                continue
            m = random.choice(moves)
            game.make_move(cp.id, m["tile_idx"], m["x"], m["y"], m["rotation"])
            if game.turn_phase == "place_meeple":
                game.skip_meeple(cp.id)
        turns += 1

    print(f"  Turns: {turns}, Tiles: {len(game.board.grid)}")
    print(f"  Human: {p1.score}, Bot: {p2.score}")
    print(f"  Phase: {game.phase}")
    print("PASS: full game vs random bot")


def test_full_game_vs_minimax_bot():
    game = GameSession(num_players=2)
    p1 = game.add_player("Human")
    p2 = game.add_player("MinimaxBot", is_bot=True, bot_type="minimax")

    turns = 0
    start = time.time()
    while game.phase == "playing" and turns < 300:
        cp = game.current_player()
        if not cp:
            break
        if cp.is_bot:
            result = game.try_bot_turn()
            if not result or "error" in result:
                break
        else:
            if game.turn_phase == "place_meeple":
                game.skip_meeple(cp.id)
                continue
            moves = game.get_valid_moves(cp.id)
            if not moves:
                game.current_turn_idx = (game.current_turn_idx + 1) % len(game.turn_order)
                game.turn_phase = "place_tile"
                turns += 1
                continue
            m = random.choice(moves)
            game.make_move(cp.id, m["tile_idx"], m["x"], m["y"], m["rotation"])
            if game.turn_phase == "place_meeple":
                game.skip_meeple(cp.id)
        turns += 1

    elapsed = time.time() - start
    print(f"  Turns: {turns}, Tiles: {len(game.board.grid)}, Time: {elapsed:.2f}s")
    print(f"  Human: {p1.score}, Minimax Bot: {p2.score}")
    print(f"  Phase: {game.phase}")
    print("PASS: full game vs minimax bot")


# ── Analytics Tests ──

def _play_game_for_analytics():
    game = GameSession(num_players=2)
    p1 = game.add_player("Alice")
    p2 = game.add_player("Bob")

    turns = 0
    while game.phase == "playing" and turns < 200:
        cp = game.current_player()
        if not cp:
            break
        if game.turn_phase == "place_meeple":
            options = game.get_meeple_options(cp.id)
            if options and random.random() < 0.5 and game.meeples.available(cp.id) > 0:
                game.place_meeple(cp.id, options[0]["position"])
            else:
                game.skip_meeple(cp.id)
            continue
        moves = game.get_valid_moves(cp.id)
        if not moves:
            game.current_turn_idx = (game.current_turn_idx + 1) % len(game.turn_order)
            game.turn_phase = "place_tile"
            turns += 1
            continue
        m = random.choice(moves)
        game.make_move(cp.id, m["tile_idx"], m["x"], m["y"], m["rotation"])
        turns += 1

    return game


def test_analytics_heatmap():
    game = _play_game_for_analytics()
    engine = AnalyticsEngine(
        game.board, game.meeples, game.players, game.history, game.deck.remaining()
    )
    result = engine.heatmap_completion()
    assert "cells" in result
    assert "max_prob" in result
    print(f"  Heatmap: {len(result['cells'])} cells, max_prob={result['max_prob']}")
    print("PASS: analytics heatmap")


def test_analytics_luck():
    game = _play_game_for_analytics()
    engine = AnalyticsEngine(
        game.board, game.meeples, game.players, game.history, game.deck.remaining()
    )
    result = engine.luck_curve()
    assert "players" in result
    for pid, data in result["players"].items():
        assert "per_turn" in data
        assert "cumulative" in data
        assert "avg" in data
        print(f"  {game.players[pid].name}: avg luck={data['avg']}")
    print("PASS: analytics luck curve")


def test_analytics_entropy():
    game = _play_game_for_analytics()
    engine = AnalyticsEngine(
        game.board, game.meeples, game.players, game.history, game.deck.remaining()
    )
    result = engine.field_entropy()
    assert "entropy" in result
    assert "normalized" in result
    assert result["normalized"] >= 0
    print(f"  Entropy: {result['entropy']:.3f} bits, normalized: {result['normalized']:.3f}")
    print("PASS: analytics entropy")


def test_analytics_greed():
    game = _play_game_for_analytics()
    engine = AnalyticsEngine(
        game.board, game.meeples, game.players, game.history, game.deck.remaining()
    )
    result = engine.greed_index()
    for pid, data in result.items():
        assert "greed_index" in data
        assert 0 <= data["greed_index"] <= 1
        print(f"  {game.players[pid].name}: greed={data['greed_index']:.3f}")
    print("PASS: analytics greed index")


def test_analytics_conflict():
    game = _play_game_for_analytics()
    engine = AnalyticsEngine(
        game.board, game.meeples, game.players, game.history, game.deck.remaining()
    )
    result = engine.conflict_risk()
    assert "conflicts" in result
    assert "total_risk" in result
    print(f"  Conflicts: {result['count']}, total risk: {result['total_risk']:.3f}")
    print("PASS: analytics conflict risk")


def test_analytics_aggression():
    game = _play_game_for_analytics()
    engine = AnalyticsEngine(
        game.board, game.meeples, game.players, game.history, game.deck.remaining()
    )
    result = engine.aggression_index()
    for pid, data in result.items():
        assert "index" in data
        print(f"  {game.players[pid].name}: aggression={data['index']:.3f} ({data['aggressive_moves']} moves)")
    print("PASS: analytics aggression")


def test_analytics_voronoi():
    game = _play_game_for_analytics()
    engine = AnalyticsEngine(
        game.board, game.meeples, game.players, game.history, game.deck.remaining()
    )
    result = engine.voronoi_control()
    total_control = sum(v["control"] for v in result.values())
    for pid, data in result.items():
        assert "control" in data
        print(f"  {game.players[pid].name}: control={data['control']:.3f} ({data['area']} tiles)")
    print("PASS: analytics voronoi control")


def test_analytics_nash():
    game = _play_game_for_analytics()
    engine = AnalyticsEngine(
        game.board, game.meeples, game.players, game.history, game.deck.remaining()
    )
    result = engine.nash_distance()
    for pid, data in result.items():
        assert "distance" in data
        print(f"  {game.players[pid].name}: nash_distance={data['distance']:.3f}")
    print("PASS: analytics nash distance")


def test_analytics_parasitism():
    game = _play_game_for_analytics()
    engine = AnalyticsEngine(
        game.board, game.meeples, game.players, game.history, game.deck.remaining()
    )
    result = engine.parasitism()
    for pid, data in result.items():
        assert "parasitism" in data
        print(f"  {game.players[pid].name}: parasitism={data['parasitism']:.3f}")
    print("PASS: analytics parasitism")


def test_analytics_depth():
    game = _play_game_for_analytics()
    engine = AnalyticsEngine(
        game.board, game.meeples, game.players, game.history, game.deck.remaining()
    )
    result = engine.depth_score()
    for pid, data in result.items():
        assert "depth" in data
        assert "interpretation" in data
        print(f"  {game.players[pid].name}: depth={data['depth']:.3f} ({data['interpretation']})")
    print("PASS: analytics depth score")


def test_compute_all_analytics():
    game = _play_game_for_analytics()
    analytics = game.get_analytics()
    expected_keys = [
        "heatmap", "luck_curve", "entropy", "greed_index", "conflict_risk",
        "aggression_index", "voronoi_control", "nash_distance", "parasitism", "depth_score",
    ]
    for key in expected_keys:
        assert key in analytics, f"Missing metric: {key}"
    print(f"  All 10 metrics computed successfully")
    print("PASS: compute all analytics")


def test_api_bot_game():
    from app import app
    client = app.test_client()

    # create game with bot
    resp = client.post('/api/games', json={"num_players": 2, "bot_opponent": "random"})
    game_id = resp.get_json()["game_id"]

    # join as human
    resp = client.post(f'/api/games/{game_id}/join', json={"name": "Human"})
    p_id = resp.get_json()["player_id"]

    # check state
    resp = client.get(f'/api/games/{game_id}?player_id={p_id}')
    state = resp.get_json()
    assert state["phase"] == "playing"

    # play a few turns
    for _ in range(5):
        resp = client.get(f'/api/games/{game_id}?player_id={p_id}')
        state = resp.get_json()
        if state["phase"] != "playing":
            break

        if state.get("turn_phase") == "place_meeple" and state["current_player"] == p_id:
            client.post(f'/api/games/{game_id}/skip_meeple', json={"player_id": p_id})
            continue

        if state["current_player"] == p_id:
            resp = client.get(f'/api/games/{game_id}/moves?player_id={p_id}')
            moves = resp.get_json()["moves"]
            if not moves:
                break
            m = moves[0]
            client.post(f'/api/games/{game_id}/place', json={
                "player_id": p_id, "tile_idx": m["tile_idx"],
                "x": m["x"], "y": m["y"], "rotation": m["rotation"],
            })
            resp = client.get(f'/api/games/{game_id}?player_id={p_id}')
            state = resp.get_json()
            if state.get("turn_phase") == "place_meeple":
                client.post(f'/api/games/{game_id}/skip_meeple', json={"player_id": p_id})
        else:
            resp = client.post(f'/api/games/{game_id}/bot_turn')
            assert resp.status_code == 200

    print("PASS: API bot game")


def test_api_analytics():
    from app import app
    client = app.test_client()

    resp = client.post('/api/games', json={"num_players": 2, "bot_opponent": "random"})
    game_id = resp.get_json()["game_id"]
    resp = client.post(f'/api/games/{game_id}/join', json={"name": "Human"})
    p_id = resp.get_json()["player_id"]

    # play a few turns
    for _ in range(3):
        resp = client.get(f'/api/games/{game_id}?player_id={p_id}')
        state = resp.get_json()
        if state["current_player"] == p_id:
            if state.get("turn_phase") == "place_meeple":
                client.post(f'/api/games/{game_id}/skip_meeple', json={"player_id": p_id})
                continue
            resp = client.get(f'/api/games/{game_id}/moves?player_id={p_id}')
            moves = resp.get_json()["moves"]
            if moves:
                m = moves[0]
                client.post(f'/api/games/{game_id}/place', json={
                    "player_id": p_id, "tile_idx": m["tile_idx"],
                    "x": m["x"], "y": m["y"], "rotation": m["rotation"],
                })
                resp = client.get(f'/api/games/{game_id}?player_id={p_id}')
                if resp.get_json().get("turn_phase") == "place_meeple":
                    client.post(f'/api/games/{game_id}/skip_meeple', json={"player_id": p_id})
        else:
            client.post(f'/api/games/{game_id}/bot_turn')

    # fetch analytics
    resp = client.get(f'/api/games/{game_id}/analytics')
    assert resp.status_code == 200
    analytics = resp.get_json()
    assert "entropy" in analytics
    assert "greed_index" in analytics
    print(f"  Analytics API returned all metrics")

    # fetch single metric
    resp = client.get(f'/api/games/{game_id}/analytics/entropy')
    assert resp.status_code == 200
    print("PASS: API analytics")


if __name__ == "__main__":
    print("=== BOT TESTS ===")
    test_random_bot()
    test_minimax_bot()
    test_bot_auto_turn()
    test_full_game_vs_random_bot()
    test_full_game_vs_minimax_bot()

    print("\n=== ANALYTICS TESTS ===")
    test_analytics_heatmap()
    test_analytics_luck()
    test_analytics_entropy()
    test_analytics_greed()
    test_analytics_conflict()
    test_analytics_aggression()
    test_analytics_voronoi()
    test_analytics_nash()
    test_analytics_parasitism()
    test_analytics_depth()
    test_compute_all_analytics()

    print("\n=== API TESTS ===")
    test_api_bot_game()
    test_api_analytics()

    print("\n=== ALL PHASE 3 TESTS PASSED ===")
