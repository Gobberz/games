import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.tile import (
    TileDef, PlacedTile, EdgeType, CenterType,
    TILE_DEFS, create_placed_tile, SIDE_INDEX, OPPOSITE
)
from game.board import Board
from game.deck import Deck
from game.session import GameSession


def test_tile_rotation():
    td = TileDef("test", [2, 0, 1, 0], [(0, 2)], CenterType.ROAD)
    tile = create_placed_tile(td, rotation=0)
    assert tile.get_rotated_edges() == [2, 0, 1, 0], f"0deg: {tile.get_rotated_edges()}"

    tile90 = create_placed_tile(td, rotation=90)
    assert tile90.get_rotated_edges() == [0, 2, 0, 1], f"90deg: {tile90.get_rotated_edges()}"

    tile180 = create_placed_tile(td, rotation=180)
    assert tile180.get_rotated_edges() == [1, 0, 2, 0], f"180deg: {tile180.get_rotated_edges()}"

    tile270 = create_placed_tile(td, rotation=270)
    assert tile270.get_rotated_edges() == [0, 1, 0, 2], f"270deg: {tile270.get_rotated_edges()}"
    print("PASS: tile rotation")


def test_tile_get_edge():
    # start tile: [2, 1, 0, 1] - N=city, E=road, S=field, W=road
    td = TileDef("start", [2, 1, 0, 1], [(1, 3)], CenterType.ROAD)
    tile = create_placed_tile(td, rotation=0)
    assert tile.get_edge("N") == 2
    assert tile.get_edge("E") == 1
    assert tile.get_edge("S") == 0
    assert tile.get_edge("W") == 1

    tile90 = create_placed_tile(td, rotation=90)
    # rotated 90: [1, 2, 1, 0]
    assert tile90.get_edge("N") == 1
    assert tile90.get_edge("E") == 2
    assert tile90.get_edge("S") == 1
    assert tile90.get_edge("W") == 0
    print("PASS: tile get_edge")


def test_board_start_tile():
    board = Board()
    assert (0, 0) in board.grid
    start = board.grid[(0, 0)]
    assert start.tile_type == "start"
    assert len(board.open_slots) > 0
    assert (0, -1) in board.open_slots  # north
    assert (1, 0) in board.open_slots   # east
    assert (0, 1) in board.open_slots   # south
    assert (-1, 0) in board.open_slots  # west
    print("PASS: board start tile")


def test_placement_validation():
    board = Board()
    # start tile: N=city(2), E=road(1), S=field(0), W=road(1)

    # straight_road: [1, 0, 1, 0] - N=road, E=field, S=road, W=field
    straight = next(d for d in TILE_DEFS if d.tile_type == "straight_road")

    # place to the east (1,0): start's E=road(1), so we need our W=road
    # straight at 0deg: N=road, E=field, S=road, W=field -> W=field(0) != road(1) -> invalid
    assert not board._is_placement_valid(straight, (1, 0), 0)

    # straight at 90deg: [0, 1, 0, 1] -> W=road(1) ✓
    assert board._is_placement_valid(straight, (1, 0), 90)

    # place to the north (0,-1): start's N=city(2), so we need our S=city
    # city_edge: [2, 0, 0, 0] at 0deg: S=field -> invalid
    city_edge = next(d for d in TILE_DEFS if d.tile_type == "city_edge")
    assert not board._is_placement_valid(city_edge, (0, -1), 0)

    # city_edge at 180deg: [0, 0, 2, 0] -> S=city(2) ✓
    assert board._is_placement_valid(city_edge, (0, -1), 180)

    print("PASS: placement validation")


def test_place_tile():
    board = Board()
    straight = next(d for d in TILE_DEFS if d.tile_type == "straight_road")

    result = board.place_tile(straight, (1, 0), 90)
    assert result is not None
    assert (1, 0) in board.grid
    assert (2, 0) in board.open_slots

    # can't place on occupied
    result2 = board.place_tile(straight, (1, 0), 90)
    assert result2 is None

    print("PASS: place tile")


def test_graph_connectivity():
    board = Board()
    straight = next(d for d in TILE_DEFS if d.tile_type == "straight_road")

    board.place_tile(straight, (1, 0), 90)
    # start tile has road E-W, straight at 90deg has road N-S (which becomes E-W after rotation)
    # check external edge exists between (0,0,E) and (1,0,W)
    assert board.feature_graph.has_edge((0, 0, "E"), (1, 0, "W"))
    print("PASS: graph connectivity")


def test_multiple_placements():
    board = Board()
    # start: N=city, E=road, S=field, W=road
    straight = next(d for d in TILE_DEFS if d.tile_type == "straight_road")
    curve = next(d for d in TILE_DEFS if d.tile_type == "curve_road")

    # East: need W=road -> straight@90 gives [0,1,0,1] W=road
    r = board.place_tile(straight, (1, 0), 90)
    assert r is not None

    # West: need E=road -> straight@90 gives [0,1,0,1] E=road
    r = board.place_tile(straight, (-1, 0), 90)
    assert r is not None

    # South of start: need N=field -> field tile like monastery [0,0,0,0]
    monastery = next(d for d in TILE_DEFS if d.tile_type == "monastery")
    r = board.place_tile(monastery, (0, 1), 0)
    assert r is not None

    assert len(board.grid) == 4
    print("PASS: multiple placements")


def test_deck():
    deck = Deck(shuffle=False)
    total = sum(d.count for d in TILE_DEFS if d.tile_type != "start")
    assert deck.remaining() == total, f"Expected {total}, got {deck.remaining()}"

    tile = deck.draw()
    assert tile is not None
    assert deck.remaining() == total - 1
    print("PASS: deck")


def test_game_session():
    game = GameSession(num_players=2)
    p1 = game.add_player("Alice")
    assert game.phase == "waiting"

    p2 = game.add_player("Bob")
    assert game.phase == "playing"
    assert len(p1.hand) == 2
    assert len(p2.hand) == 2

    cp = game.current_player()
    assert cp is not None
    assert cp.id == p1.id
    print("PASS: game session")


def test_valid_moves():
    game = GameSession(num_players=2)
    p1 = game.add_player("Alice")
    p2 = game.add_player("Bob")

    moves = game.get_valid_moves(p1.id)
    assert len(moves) > 0, "Should have valid moves"
    print(f"  Player has {len(moves)} valid moves")
    print("PASS: valid moves")


def test_make_move():
    game = GameSession(num_players=2)
    p1 = game.add_player("Alice")
    p2 = game.add_player("Bob")

    moves = game.get_valid_moves(p1.id)
    if moves:
        m = moves[0]
        result = game.make_move(p1.id, m["tile_idx"], m["x"], m["y"], m["rotation"])
        assert "success" in result, f"Move failed: {result}"
        # may be in place_meeple phase, skip to advance turn
        if game.turn_phase == "place_meeple":
            game.skip_meeple(p1.id)
        assert game.current_player().id == p2.id
        print("PASS: make move")
    else:
        print("SKIP: no valid moves (unusual)")


def test_wrong_turn():
    game = GameSession(num_players=2)
    p1 = game.add_player("Alice")
    p2 = game.add_player("Bob")

    result = game.make_move(p2.id, 0, 1, 0, 0)
    assert "error" in result
    print("PASS: wrong turn rejection")


def test_full_game_simulation():
    game = GameSession(num_players=2)
    p1 = game.add_player("Alice")
    p2 = game.add_player("Bob")

    turns = 0
    max_turns = 200
    stuck = 0

    while game.phase == "playing" and turns < max_turns:
        cp = game.current_player()

        if game.turn_phase == "place_meeple":
            game.skip_meeple(cp.id)
            continue

        moves = game.get_valid_moves(cp.id)
        if not moves:
            stuck += 1
            if stuck > 10:
                break
            game.current_turn_idx = (game.current_turn_idx + 1) % len(game.turn_order)
            continue

        stuck = 0
        import random
        m = random.choice(moves)
        result = game.make_move(cp.id, m["tile_idx"], m["x"], m["y"], m["rotation"])
        assert "success" in result, f"Move failed at turn {turns}: {result}"
        turns += 1

    print(f"  Simulated {turns} turns, {len(game.board.grid)} tiles on board")
    print(f"  Deck remaining: {game.deck.remaining()}")
    print("PASS: full game simulation")


def test_city_completion():
    board = Board()
    city_edge = next(d for d in TILE_DEFS if d.tile_type == "city_edge")

    # place city_edge at 180deg north of start: its S=city matches start's N=city
    board.place_tile(city_edge, (0, -1), 180)

    city_features = board.get_features(EdgeType.CITY)
    for feat in city_features:
        complete = board.is_feature_complete(feat, EdgeType.CITY)
        if len(feat) >= 2:
            print(f"  City feature size={len(feat)}, complete={complete}")

    print("PASS: city completion check")


def test_serialization():
    game = GameSession(num_players=2)
    p1 = game.add_player("Alice")
    p2 = game.add_player("Bob")

    state = game.to_dict(for_player=p1.id)
    assert "board" in state
    assert "players" in state
    assert "tiles" in state["board"]
    assert "0,0" in state["board"]["tiles"]

    # ensure opponent hand is hidden
    assert "hand" not in state["players"][p2.id]
    # ensure own hand is visible
    assert "hand" in state["players"][p1.id]
    print("PASS: serialization")


if __name__ == "__main__":
    test_tile_rotation()
    test_tile_get_edge()
    test_board_start_tile()
    test_placement_validation()
    test_place_tile()
    test_graph_connectivity()
    test_multiple_placements()
    test_deck()
    test_game_session()
    test_valid_moves()
    test_make_move()
    test_wrong_turn()
    test_full_game_simulation()
    test_city_completion()
    test_serialization()
    print("\n=== ALL TESTS PASSED ===")
