# Carcassonne Analytics

A full Carcassonne implementation with AI bots, 10 strategic analytics metrics, and custom game mechanics.

## Quick Start

```bash
pip install -r requirements.txt
python app.py
# Open http://localhost:5000
```

## Architecture

- **Backend**: Flask REST API + NetworkX graph-based tile engine
- **Frontend**: Konva.js canvas with dark theme UI
- **AI**: RandomBot + MinimaxBot (heuristic evaluation with board simulation)

## Game Engine

| Module | Description |
|--------|-------------|
| `tile.py` | 17 tile types, rotation system, edge matching |
| `board.py` | NetworkX feature graph, placement validation |
| `deck.py` | Shuffled deck management |
| `scoring.py` | Meeple manager + full scoring (roads, cities, monasteries, fields) |
| `bots.py` | RandomBot + MinimaxBot with multi-factor evaluation |
| `analytics.py` | 10 strategic metrics engine |
| `engineer.py` | Engineer meeple — rotate placed tiles |
| `objectives.py` | 10 hidden objective cards with end-game bonuses |
| `session.py` | Game session orchestrator with custom rules |

## Custom Mechanics

### Engineer (one-time ability)
Rotate any already-placed tile 90°. Cannot target start tile or tiles with opponent meeples. Validates edge matching after rotation.

### Hidden Objectives (2 per player)
Secret goals dealt at game start. Evaluated at end for bonus points (6-12 pts):
- Road King, City Lord, Monk Master, Field Baron
- Expansionist, Meeple Hoarder, Conqueror, Renaissance
- Late Bloomer, Wall Builder

### Strategic Reserve
Hand size of 2 tiles (configurable) — choose which tile to play.

## Analytics (10 Metrics)

1. **Heatmap Completion** — Monte Carlo probability of city completion per tile
2. **Luck Curve** — tile value deviation from mean, cumulative per player
3. **Field Entropy** — Shannon entropy over board slot compatibility
4. **Greed Index** — current score / (score + meeple potential)
5. **Conflict Risk** — proximity of opponent-occupied incomplete cities
6. **Aggression Index** — % of moves disrupting opponent features
7. **Voronoi Control** — territory allocation by Manhattan distance from meeples
8. **Nash Distance** — deviation from locally optimal moves
9. **Parasitism** — % of features shared with opponents
10. **Depth Score** — ratio of setup moves vs immediate scoring (tactical/strategic)

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/games` | POST | Create game (with optional bot + rules) |
| `/api/games/<id>/join` | POST | Join game |
| `/api/games/<id>` | GET | Get game state |
| `/api/games/<id>/moves` | GET | Valid tile placements |
| `/api/games/<id>/place` | POST | Place tile |
| `/api/games/<id>/meeple` | POST | Place meeple |
| `/api/games/<id>/skip_meeple` | POST | Skip meeple |
| `/api/games/<id>/engineer` | POST | Use engineer ability |
| `/api/games/<id>/engineer_targets` | GET | Valid engineer targets |
| `/api/games/<id>/bot_turn` | POST | Trigger bot move |
| `/api/games/<id>/analytics` | GET | All 10 metrics |
| `/api/games/<id>/analytics/<metric>` | GET | Single metric |

## Tests

```bash
python tests/test_phase1.py   # 16 tests — tile engine, board, placement
python tests/test_phase2.py   # 15 tests — scoring, meeples, features
python tests/test_phase3.py   # 19 tests — bots, analytics, API
python tests/test_phase4.py   # 16 tests — engineer, objectives, rules
python tests/test_api.py      # 3 tests — REST API integration
python tests/test_stress.py   # 20 full game simulations
# Total: 70 tests, 0 failures
```

## Controls

- **Click** tile in hand → select
- **R** → rotate selected tile
- **Click** green slot → place tile
- **Click** red circle → place meeple
- **H** → toggle completion heatmap
- **🔧 Engineer** button → activate engineer mode
- **Pan** → drag board
- **Zoom** → scroll wheel
