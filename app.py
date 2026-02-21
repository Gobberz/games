from flask import Flask, request, jsonify, send_from_directory
from game.session import GameSession

app = Flask(__name__, static_folder="static", template_folder="templates")
games = {}


@app.route("/")
def index():
    return send_from_directory("templates", "index.html")


# ── Game Lifecycle ──

@app.route("/api/games", methods=["POST"])
def create_game():
    data = request.json or {}
    num_players = data.get("num_players", 2)
    bot_opponent = data.get("bot_opponent")
    custom_rules = data.get("rules", {})
    game = GameSession(num_players=num_players, custom_rules=custom_rules)
    games[game.id] = game

    if bot_opponent:
        game.add_player(f"Bot ({bot_opponent.title()})", is_bot=True, bot_type=bot_opponent)

    return jsonify({"game_id": game.id, "rules": game.rules})


@app.route("/api/games/<game_id>/join", methods=["POST"])
def join_game(game_id):
    game = games.get(game_id)
    if not game:
        return jsonify({"error": "Game not found"}), 404
    data = request.json or {}
    name = data.get("name", "Player")
    if len(game.players) >= game.num_players:
        return jsonify({"error": "Game is full"}), 400
    player = game.add_player(name)
    return jsonify({"player_id": player.id, "name": player.name, "rules": game.rules})


@app.route("/api/games/<game_id>", methods=["GET"])
def get_game(game_id):
    game = games.get(game_id)
    if not game:
        return jsonify({"error": "Game not found"}), 404
    player_id = request.args.get("player_id")
    return jsonify(game.to_dict(for_player=player_id))


# ── Tile Placement ──

@app.route("/api/games/<game_id>/moves", methods=["GET"])
def get_moves(game_id):
    game = games.get(game_id)
    if not game:
        return jsonify({"error": "Game not found"}), 404
    player_id = request.args.get("player_id")
    return jsonify({"moves": game.get_valid_moves(player_id)})


@app.route("/api/games/<game_id>/place", methods=["POST"])
def place_tile(game_id):
    game = games.get(game_id)
    if not game:
        return jsonify({"error": "Game not found"}), 404
    data = request.json or {}
    player_id = data.get("player_id")
    if not player_id:
        return jsonify({"error": "player_id required"}), 400

    result = game.make_move(
        player_id, data.get("tile_idx", 0),
        data.get("x", 0), data.get("y", 0), data.get("rotation", 0),
    )
    if "error" in result:
        return jsonify(result), 400

    return jsonify({
        "success": True,
        "move": result["move"],
        "meeple_options": result.get("meeple_options", []),
        "game": game.to_dict(for_player=player_id),
    })


# ── Meeple ──

@app.route("/api/games/<game_id>/meeple", methods=["POST"])
def place_meeple(game_id):
    game = games.get(game_id)
    if not game:
        return jsonify({"error": "Game not found"}), 404
    data = request.json or {}
    player_id = data.get("player_id")
    position = data.get("position")
    if not player_id or not position:
        return jsonify({"error": "player_id and position required"}), 400

    result = game.place_meeple(player_id, position)
    if "error" in result:
        return jsonify(result), 400
    return jsonify({
        "success": True,
        "score_events": result.get("score_events", []),
        "game": game.to_dict(for_player=player_id),
    })


@app.route("/api/games/<game_id>/skip_meeple", methods=["POST"])
def skip_meeple(game_id):
    game = games.get(game_id)
    if not game:
        return jsonify({"error": "Game not found"}), 404
    data = request.json or {}
    player_id = data.get("player_id")
    if not player_id:
        return jsonify({"error": "player_id required"}), 400

    result = game.skip_meeple(player_id)
    if "error" in result:
        return jsonify(result), 400
    return jsonify({
        "success": True,
        "score_events": result.get("score_events", []),
        "game": game.to_dict(for_player=player_id),
    })


@app.route("/api/games/<game_id>/meeple_options", methods=["GET"])
def get_meeple_options(game_id):
    game = games.get(game_id)
    if not game:
        return jsonify({"error": "Game not found"}), 404
    player_id = request.args.get("player_id")
    if not player_id:
        return jsonify({"error": "player_id required"}), 400
    return jsonify({"options": game.get_meeple_options(player_id)})


# ── Engineer ──

@app.route("/api/games/<game_id>/engineer", methods=["POST"])
def use_engineer(game_id):
    game = games.get(game_id)
    if not game:
        return jsonify({"error": "Game not found"}), 404
    data = request.json or {}
    player_id = data.get("player_id")
    target_x = data.get("x", 0)
    target_y = data.get("y", 0)
    if not player_id:
        return jsonify({"error": "player_id required"}), 400

    result = game.use_engineer(player_id, target_x, target_y)
    if "error" in result:
        return jsonify(result), 400
    return jsonify({
        "success": True,
        "rotated": result.get("rotated"),
        "score_events": result.get("score_events", []),
        "game": game.to_dict(for_player=player_id),
    })


@app.route("/api/games/<game_id>/engineer_targets", methods=["GET"])
def engineer_targets(game_id):
    game = games.get(game_id)
    if not game:
        return jsonify({"error": "Game not found"}), 404
    player_id = request.args.get("player_id")
    if not player_id:
        return jsonify({"error": "player_id required"}), 400
    return jsonify({"targets": game.get_engineer_targets(player_id)})


# ── Bot ──

@app.route("/api/games/<game_id>/bot_turn", methods=["POST"])
def bot_turn(game_id):
    game = games.get(game_id)
    if not game:
        return jsonify({"error": "Game not found"}), 404
    cp = game.current_player()
    if not cp or not cp.is_bot:
        return jsonify({"error": "Current player is not a bot"}), 400

    results = []
    for _ in range(5):
        cp = game.current_player()
        if not cp or not cp.is_bot or game.phase != "playing":
            break
        result = game.try_bot_turn()
        if result:
            results.append(result)

    return jsonify({
        "success": True,
        "bot_actions": len(results),
        "game": game.to_dict(),
    })


# ── Analytics ──

@app.route("/api/games/<game_id>/analytics", methods=["GET"])
def get_analytics(game_id):
    game = games.get(game_id)
    if not game:
        return jsonify({"error": "Game not found"}), 404
    return jsonify(game.get_analytics())


@app.route("/api/games/<game_id>/analytics/<metric>", methods=["GET"])
def get_metric(game_id, metric):
    game = games.get(game_id)
    if not game:
        return jsonify({"error": "Game not found"}), 404
    analytics = game.get_analytics()
    if metric not in analytics:
        return jsonify({"error": f"Unknown metric: {metric}"}), 404
    return jsonify({metric: analytics[metric]})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
