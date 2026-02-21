import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from app import app


def test_api():
    client = app.test_client()

    # create game
    resp = client.post('/api/games', json={"num_players": 2})
    assert resp.status_code == 200
    data = resp.get_json()
    game_id = data["game_id"]
    print(f"  Created game: {game_id}")

    # join player 1
    resp = client.post(f'/api/games/{game_id}/join', json={"name": "Alice"})
    assert resp.status_code == 200
    p1 = resp.get_json()
    p1_id = p1["player_id"]
    print(f"  Player 1 joined: {p1_id}")

    # join player 2
    resp = client.post(f'/api/games/{game_id}/join', json={"name": "Bob"})
    assert resp.status_code == 200
    p2 = resp.get_json()
    p2_id = p2["player_id"]
    print(f"  Player 2 joined: {p2_id}")

    # get game state
    resp = client.get(f'/api/games/{game_id}?player_id={p1_id}')
    assert resp.status_code == 200
    state = resp.get_json()
    assert state["phase"] == "playing"
    assert state["current_player"] == p1_id
    print(f"  Game phase: {state['phase']}")

    # get valid moves
    resp = client.get(f'/api/games/{game_id}/moves?player_id={p1_id}')
    assert resp.status_code == 200
    moves_data = resp.get_json()
    moves = moves_data["moves"]
    assert len(moves) > 0
    print(f"  Valid moves: {len(moves)}")

    # make a move
    m = moves[0]
    resp = client.post(f'/api/games/{game_id}/place', json={
        "player_id": p1_id,
        "tile_idx": m["tile_idx"],
        "x": m["x"],
        "y": m["y"],
        "rotation": m["rotation"],
    })
    assert resp.status_code == 200
    result = resp.get_json()
    assert result["success"]
    print(f"  Move made: ({m['x']},{m['y']}) rot={m['rotation']}")

    # handle meeple phase if needed
    state = result["game"]
    if state["turn_phase"] == "place_meeple":
        resp = client.post(f'/api/games/{game_id}/skip_meeple', json={
            "player_id": p1_id,
        })
        assert resp.status_code == 200

    # verify turn advanced
    resp = client.get(f'/api/games/{game_id}?player_id={p1_id}')
    state = resp.get_json()
    assert state["current_player"] == p2_id
    print(f"  Turn advanced to player 2")

    # wrong turn should fail
    resp = client.post(f'/api/games/{game_id}/place', json={
        "player_id": p1_id,
        "tile_idx": 0, "x": 0, "y": 1, "rotation": 0,
    })
    assert resp.status_code == 400
    print(f"  Wrong turn correctly rejected")

    # play a few more turns
    for turn in range(10):
        resp = client.get(f'/api/games/{game_id}?player_id={p1_id}')
        state = resp.get_json()

        if state.get("turn_phase") == "place_meeple":
            cp_id = state["current_player"]
            client.post(f'/api/games/{game_id}/skip_meeple', json={"player_id": cp_id})
            continue

        cp_id = state["current_player"]
        if not cp_id:
            break

        resp = client.get(f'/api/games/{game_id}/moves?player_id={cp_id}')
        moves = resp.get_json()["moves"]
        if not moves:
            break

        m = moves[0]
        resp = client.post(f'/api/games/{game_id}/place', json={
            "player_id": cp_id,
            "tile_idx": m["tile_idx"],
            "x": m["x"], "y": m["y"],
            "rotation": m["rotation"],
        })
        assert resp.status_code == 200

    print(f"  Played {turn + 1} additional turns successfully")
    print("PASS: API integration")


def test_404():
    client = app.test_client()
    resp = client.get('/api/games/nonexistent')
    assert resp.status_code == 404
    print("PASS: 404 handling")


if __name__ == "__main__":
    test_api()
    test_404()
    print("\n=== ALL API TESTS PASSED ===")
