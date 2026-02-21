import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from game.session import GameSession

errors = 0
total_games = 20

for g in range(total_games):
    game = GameSession(num_players=2)
    p1 = game.add_player("A")
    p2 = game.add_player("B")

    turns = 0
    skip_count = 0
    while game.phase == "playing" and turns < 200:
        cp = game.current_player()

        if game.turn_phase == "place_meeple":
            game.skip_meeple(cp.id)
            continue

        moves = game.get_valid_moves(cp.id)
        if not moves:
            skip_count += 1
            if skip_count > 20:
                break
            game.current_turn_idx = (game.current_turn_idx + 1) % len(game.turn_order)
            game.turn_phase = "place_tile"
            continue
        skip_count = 0
        m = random.choice(moves)
        result = game.make_move(cp.id, m["tile_idx"], m["x"], m["y"], m["rotation"])
        if "error" in result:
            errors += 1
            print(f"ERROR in game {g}, turn {turns}: {result}")
            break
        turns += 1

    state = game.to_dict()
    tiles_placed = len(game.board.grid)
    print(f"Game {g+1:2d}: {turns:3d} turns, {tiles_placed:3d} tiles, deck={game.deck.remaining()}, phase={game.phase}")

print(f"\n{'='*40}")
print(f"Ran {total_games} games, {errors} errors")
if errors == 0:
    print("ALL STRESS TESTS PASSED")
else:
    print("FAILURES DETECTED")
