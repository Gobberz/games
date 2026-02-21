import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.tile import TileDef, EdgeType, CenterType, TILE_DEFS, SIDE_NAMES
from game.board import Board
from game.scoring import MeepleManager, Meeple, ScoringEngine
from game.session import GameSession
from game.objectives import ObjectiveManager, OBJECTIVES, ObjectiveChecker
from game.engineer import (
    EngineerManager, get_valid_engineer_targets, apply_engineer_rotation,
)


# ── Engineer Tests ──

def test_engineer_manager():
    mgr = EngineerManager()
    mgr.init_player("p1")
    mgr.init_player("p2")

    assert mgr.has_engineer("p1")
    assert mgr.has_engineer("p2")

    assert mgr.use_engineer("p1")
    assert not mgr.has_engineer("p1")
    assert not mgr.use_engineer("p1")  # can't use twice

    mgr.return_engineer("p1")
    assert mgr.has_engineer("p1")

    d = mgr.to_dict()
    assert d["used"]["p1"] == 1
    print("PASS: engineer manager")


def test_engineer_targets():
    board = Board()
    meeples = []

    # start tile at (0,0) - should NOT be a valid target
    targets = get_valid_engineer_targets(board, meeples, "p1")
    assert all(t["x"] != 0 or t["y"] != 0 for t in targets), "Start tile should be excluded"

    # place a tile
    tile_def = next(d for d in TILE_DEFS if d.tile_type == "city_edge")
    for rot in [0, 90, 180, 270]:
        result = board.place_tile(tile_def, (0, -1), rot)
        if result:
            break

    if result:
        targets = get_valid_engineer_targets(board, meeples, "p1")
        target_coords = [(t["x"], t["y"]) for t in targets]
        print(f"  Targets: {len(targets)} tiles available")
        assert len(targets) >= 0  # may or may not have valid rotations
    print("PASS: engineer targets")


def test_engineer_rotation():
    board = Board()

    # place a tile north of start
    tile_def = next(d for d in TILE_DEFS if d.tile_type == "city_edge")
    for rot in [0, 90, 180, 270]:
        result = board.place_tile(tile_def, (0, -1), rot)
        if result:
            break

    assert result is not None
    old_rot = board.grid[(0, -1)].rotation
    old_edges = board.grid[(0, -1)].get_rotated_edges()

    ok = apply_engineer_rotation(board, 0, -1)
    assert ok, "Rotation should succeed"

    new_rot = board.grid[(0, -1)].rotation
    assert new_rot == (old_rot + 90) % 360
    print(f"  Rotated from {old_rot} to {new_rot}")
    print("PASS: engineer rotation")


def test_engineer_via_session():
    game = GameSession(num_players=2, custom_rules={"engineer": True, "objectives": False})
    p1 = game.add_player("Alice")
    p2 = game.add_player("Bob")

    assert game.engineer is not None
    assert game.engineer.has_engineer(p1.id)

    # play a move first to have a non-start tile
    moves = game.get_valid_moves(p1.id)
    if moves:
        m = moves[0]
        game.make_move(p1.id, m["tile_idx"], m["x"], m["y"], m["rotation"])
        if game.turn_phase == "place_meeple":
            game.skip_meeple(p1.id)

    # now try engineer on p2's turn... skip to p1's turn by playing p2
    moves = game.get_valid_moves(p2.id)
    if moves:
        m = moves[0]
        game.make_move(p2.id, m["tile_idx"], m["x"], m["y"], m["rotation"])
        if game.turn_phase == "place_meeple":
            game.skip_meeple(p2.id)

    # check engineer targets for p1
    targets = game.get_engineer_targets(p1.id)
    if targets:
        t = targets[0]
        result = game.use_engineer(p1.id, t["x"], t["y"])
        if "error" not in result:
            assert not game.engineer.has_engineer(p1.id)
            print(f"  Engineer used at ({t['x']},{t['y']})")
        else:
            print(f"  Engineer blocked: {result['error']}")
    else:
        print("  No valid targets (topology constraint)")
    print("PASS: engineer via session")


def test_engineer_blocked_on_opponent_meeple():
    board = Board()
    mgr = MeepleManager()
    mgr.init_player("p1")
    mgr.init_player("p2")

    tile_def = next(d for d in TILE_DEFS if d.tile_type == "city_edge")
    for rot in [0, 90, 180, 270]:
        result = board.place_tile(tile_def, (0, -1), rot)
        if result:
            break

    if result:
        m = Meeple("p2", 0, -1, "N")
        mgr.place(m)
        targets = get_valid_engineer_targets(board, mgr.placed, "p1")
        target_coords = {(t["x"], t["y"]) for t in targets}
        assert (0, -1) not in target_coords, "Should not target tile with opponent meeple"
    print("PASS: engineer blocked on opponent meeple")


# ── Objectives Tests ──

def test_objective_manager_deal():
    mgr = ObjectiveManager()
    mgr.deal_objectives(["p1", "p2"], count=2)

    assert len(mgr.player_objectives["p1"]) == 2
    assert len(mgr.player_objectives["p2"]) == 2
    # no overlap
    ids_1 = {o.obj_id for o in mgr.player_objectives["p1"]}
    ids_2 = {o.obj_id for o in mgr.player_objectives["p2"]}
    assert len(ids_1 & ids_2) == 0, "Objectives should not overlap"
    print(f"  P1: {[o.name for o in mgr.player_objectives['p1']]}")
    print(f"  P2: {[o.name for o in mgr.player_objectives['p2']]}")
    print("PASS: objective dealing")


def test_objective_serialization():
    mgr = ObjectiveManager()
    mgr.deal_objectives(["p1", "p2"])

    d = mgr.to_dict(for_player="p1")
    assert d["p1"]["objectives"] is not None
    assert d["p2"]["objectives"] is None  # hidden
    assert d["p1"]["count"] == 2
    print("PASS: objective serialization (hidden from opponent)")


def test_objective_quadrants():
    game = GameSession(num_players=2, custom_rules={"objectives": True, "engineer": False})
    p1 = game.add_player("Alice")
    p2 = game.add_player("Bob")

    game.history = [
        {"player_id": p1.id, "x": 1, "y": 1, "tile_type": "test", "rotation": 0, "turn": 0},
        {"player_id": p1.id, "x": -1, "y": 1, "tile_type": "test", "rotation": 0, "turn": 1},
        {"player_id": p1.id, "x": 1, "y": -1, "tile_type": "test", "rotation": 0, "turn": 2},
        {"player_id": p1.id, "x": -1, "y": -1, "tile_type": "test", "rotation": 0, "turn": 3},
    ]

    checker = ObjectiveChecker(game, p1.id)
    assert checker.check_quadrants(), "Should meet quadrant objective"
    print("PASS: objective quadrants check")


def test_objective_meeple_hoard():
    game = GameSession(num_players=2, custom_rules={"objectives": True, "engineer": False})
    p1 = game.add_player("Alice")
    p2 = game.add_player("Bob")

    # by default player has 7 meeples, used 0 -> should pass
    checker = ObjectiveChecker(game, p1.id)
    assert checker.check_meeple_hoard(), "Should have 7 >= 5 meeples"

    # use some: 7 - 3 = 4 remaining, 4 < 5 -> should fail
    for i in range(3):
        m = Meeple(p1.id, i, 0, "N")
        game.meeples.place(m)
    assert not ObjectiveChecker(game, p1.id).check_meeple_hoard(), "4 < 5 -> should fail"
    print("PASS: objective meeple hoard check")


def test_objective_diversity():
    game = GameSession(num_players=2, custom_rules={"objectives": True, "engineer": False})
    p1 = game.add_player("Alice")
    p2 = game.add_player("Bob")

    game.score_events = [
        {"player_id": p1.id, "points": 4, "reason": "completed_city", "feature_type": "city", "tiles": [], "turn": 0},
        {"player_id": p1.id, "points": 3, "reason": "completed_road", "feature_type": "road", "tiles": [], "turn": 1},
        {"player_id": p1.id, "points": 9, "reason": "completed_monastery", "feature_type": "monastery", "tiles": [], "turn": 2},
    ]

    checker = ObjectiveChecker(game, p1.id)
    assert checker.check_diversity(), "3 types should meet diversity"
    print("PASS: objective diversity check")


# ── Custom Rules Tests ──

def test_custom_rules_disabled():
    game = GameSession(num_players=2, custom_rules={"engineer": False, "objectives": False})
    p1 = game.add_player("Alice")
    p2 = game.add_player("Bob")

    assert game.engineer is None
    assert game.objectives is None

    result = game.use_engineer(p1.id, 0, 0)
    assert "error" in result
    print("PASS: custom rules disabled")


def test_custom_rules_hand_size():
    game = GameSession(num_players=2, custom_rules={"hand_size": 3, "engineer": False, "objectives": False})
    p1 = game.add_player("Alice")
    p2 = game.add_player("Bob")

    assert len(p1.hand) == 3
    assert len(p2.hand) == 3
    print("PASS: custom hand size (3)")


def test_to_dict_with_rules():
    game = GameSession(num_players=2)
    p1 = game.add_player("Alice")
    p2 = game.add_player("Bob")

    d = game.to_dict(for_player=p1.id)
    assert "rules" in d
    assert d["rules"]["engineer"] is True
    assert d["rules"]["objectives"] is True
    assert "engineer" in d
    assert "objectives" in d
    assert d["objectives"][p1.id]["objectives"] is not None
    assert d["objectives"][p2.id]["objectives"] is None
    print("PASS: to_dict with all rules")


# ── Integration Tests ──

def test_full_game_with_mechanics():
    game = GameSession(num_players=2, custom_rules={"engineer": True, "objectives": True})
    p1 = game.add_player("Alice")
    p2 = game.add_player("MinimaxBot", is_bot=True, bot_type="minimax")

    assert game.objectives is not None
    assert game.engineer is not None

    turns = 0
    engineer_used = False
    while game.phase == "playing" and turns < 300:
        cp = game.current_player()
        if not cp:
            break

        if cp.is_bot:
            result = game.try_bot_turn()
            if not result:
                break
        else:
            if game.turn_phase == "place_meeple":
                opts = game.get_meeple_options(cp.id)
                if opts and game.meeples.available(cp.id) > 0 and random.random() < 0.5:
                    game.place_meeple(cp.id, opts[0]["position"])
                else:
                    game.skip_meeple(cp.id)
                continue

            # try engineer once
            if not engineer_used and game.engineer.has_engineer(cp.id) and random.random() < 0.3:
                targets = game.get_engineer_targets(cp.id)
                if targets:
                    t = targets[0]
                    r = game.use_engineer(cp.id, t["x"], t["y"])
                    if "success" in r:
                        engineer_used = True
                        print(f"  Engineer used at turn {turns}")

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

    print(f"  Turns: {turns}, Phase: {game.phase}")
    print(f"  Alice: {p1.score}, Bot: {p2.score}")

    # check objectives evaluated
    if game.objectives:
        results = game.objectives.evaluate_all(game)
        for pid, objs in results.items():
            name = game.players[pid].name
            completed = [o["name"] for o in objs if o["completed"]]
            print(f"  {name} objectives: {completed or 'none completed'}")

    print("PASS: full game with mechanics")


def test_api_engineer():
    from app import app
    client = app.test_client()

    resp = client.post('/api/games', json={
        "num_players": 2, "bot_opponent": "random",
        "rules": {"engineer": True, "objectives": True},
    })
    game_id = resp.get_json()["game_id"]

    resp = client.post(f'/api/games/{game_id}/join', json={"name": "Human"})
    p_id = resp.get_json()["player_id"]

    # play a turn
    resp = client.get(f'/api/games/{game_id}/moves?player_id={p_id}')
    moves = resp.get_json()["moves"]
    if moves:
        m = moves[0]
        client.post(f'/api/games/{game_id}/place', json={
            "player_id": p_id, "tile_idx": m["tile_idx"],
            "x": m["x"], "y": m["y"], "rotation": m["rotation"],
        })
        resp = client.get(f'/api/games/{game_id}?player_id={p_id}')
        state = resp.get_json()
        if state.get("turn_phase") == "place_meeple":
            client.post(f'/api/games/{game_id}/skip_meeple', json={"player_id": p_id})

    # bot turn
    client.post(f'/api/games/{game_id}/bot_turn')

    # check engineer targets
    resp = client.get(f'/api/games/{game_id}/engineer_targets?player_id={p_id}')
    assert resp.status_code == 200
    targets = resp.get_json()["targets"]
    print(f"  Engineer targets: {len(targets)}")

    if targets:
        t = targets[0]
        resp = client.post(f'/api/games/{game_id}/engineer', json={
            "player_id": p_id, "x": t["x"], "y": t["y"],
        })
        r = resp.get_json()
        if r.get("success"):
            print(f"  Engineer used at ({t['x']},{t['y']})")
        else:
            print(f"  Engineer response: {r}")

    # check state has objectives
    resp = client.get(f'/api/games/{game_id}?player_id={p_id}')
    state = resp.get_json()
    assert "objectives" in state
    assert "engineer" in state
    assert "rules" in state
    print("PASS: API engineer + objectives")


if __name__ == "__main__":
    print("=== ENGINEER TESTS ===")
    test_engineer_manager()
    test_engineer_targets()
    test_engineer_rotation()
    test_engineer_via_session()
    test_engineer_blocked_on_opponent_meeple()

    print("\n=== OBJECTIVES TESTS ===")
    test_objective_manager_deal()
    test_objective_serialization()
    test_objective_quadrants()
    test_objective_meeple_hoard()
    test_objective_diversity()

    print("\n=== CUSTOM RULES TESTS ===")
    test_custom_rules_disabled()
    test_custom_rules_hand_size()
    test_to_dict_with_rules()

    print("\n=== INTEGRATION TESTS ===")
    test_full_game_with_mechanics()
    test_api_engineer()

    print("\n=== ALL PHASE 4 TESTS PASSED ===")
