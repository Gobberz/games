# 🃏 BlackJack Trainer

**ML-powered Basic Strategy trainer for Blackjack.**  
Analyzes every move, detects error patterns through ML, and shows a heatmap of your weak spots.

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

---

## Project Structure

```
blackjack_trainer/
├── app.py                     # Streamlit entry point
├── requirements.txt
│
├── game/
│   ├── engine.py              # Card, Deck, Hand, Game
│   ├── strategy.py            # Basic Strategy table (18×10)
│   └── evaluator.py
│
├── data/
│   ├── database.py            # SQLite connection manager
│   ├── schema.py              # DDL table schema
│   ├── repository.py          # CRUD + analytics queries
│   └── game_session.py        # Facade: engine + DB
│
├── ml/
│   ├── features.py            # Feature engineering
│   ├── trainer.py             # RF + KMeans + LR
│   ├── predictor.py           # Real-time inference
│   ├── bootstrap.py           # Synthetic data (cold start)
│   └── simulation.py          # Monte Carlo simulator
│
├── ui/
│   ├── styles.py              # CSS theme + HTML helpers
│   ├── game_view.py           # Game table
│   ├── analytics_view.py      # Analytics dashboard
│   └── simulation_view.py     # Monte Carlo page
│
└── tests/
    ├── test_game.py           # 84 tests for engine and strategy
    ├── test_data.py           # 64 tests for DB layer
    ├── test_ui.py             # 35 tests for UI and simulation
    └── test_ml.py             # 46 tests for ML pipeline
```

---

## App Pages

### 🎮 Game
- Full blackjack with 6-deck shoe
- Feedback after every move: correct/mistake + what you should have done
- ML warning when you frequently mess up in similar situations

### 📊 Analytics
- **Error heatmap** — 18×10 grid showing your problem spots
- **Progress chart** — accuracy and win rate across sessions
- **Player profile** — ML cluster (Expert / Cautious / Impulsive / Chaotic)

### 🔬 Simulation
- Monte Carlo: 1k–25k rounds
- Three strategies: Basic Strategy, Beginner, Random
- EV analysis and balance over time

---

## Running Tests

```bash
python -m unittest discover -s tests -v
# Expected: Ran 235 tests ... OK
```

---

## ML Pipeline

| Model | Task | Input Features | Output |
|-------|------|---------------|--------|
| Random Forest | P(error) | player_total, dealer_upcard, is_soft, is_pair, action | Warning in UI |
| KMeans (k=4) | Play style cluster | hit_rate, stand_rate, double_rate, soft_accuracy | Player archetype |
| Logistic Reg | Accuracy by situation | Same features | Top problem spots |

**Cold start**: On first run, generates 200 synthetic moves  
(simulating a beginner) for initial model training.

**Retraining**: Automatically every 25 new moves.

---

## Basic Strategy Rules (6 decks, dealer stands on Soft 17)

- **Hard 17+** → always Stand
- **Hard 11** → Double vs 2–10, Hit vs Ace  
- **Hard 12** → Stand vs 4–6, Hit vs others
- **8-8, A-A** → always Split
- **10-10** → never Split
- **Soft 18** → Double vs 3–6, Stand vs 7–8, Hit vs 9–A
