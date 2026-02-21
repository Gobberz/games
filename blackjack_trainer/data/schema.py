SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS players (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL DEFAULT 'Player',
    created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    total_rounds  INTEGER NOT NULL DEFAULT 0,
    total_wins    INTEGER NOT NULL DEFAULT 0,
    total_losses  INTEGER NOT NULL DEFAULT 0,
    total_pushes  INTEGER NOT NULL DEFAULT 0,
    cluster_id    INTEGER,
    cluster_name  TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id     INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    started_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    ended_at      TEXT,
    num_decks     INTEGER NOT NULL DEFAULT 6,
    rounds_played INTEGER NOT NULL DEFAULT 0,
    accuracy      REAL,
    win_rate      REAL
);

CREATE TABLE IF NOT EXISTS rounds (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id          INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    round_num           INTEGER NOT NULL,
    started_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    player_cards_start  TEXT    NOT NULL,
    dealer_upcard       TEXT    NOT NULL,
    dealer_hole_card    TEXT    NOT NULL,
    player_cards_final  TEXT,
    dealer_cards_final  TEXT,
    player_final_value  INTEGER,
    dealer_final_value  INTEGER,
    result              TEXT,
    moves_total         INTEGER NOT NULL DEFAULT 0,
    moves_correct       INTEGER NOT NULL DEFAULT 0,
    round_accuracy      REAL
);

CREATE TABLE IF NOT EXISTS moves (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    round_id            INTEGER NOT NULL REFERENCES rounds(id) ON DELETE CASCADE,
    move_num            INTEGER NOT NULL,
    player_total        INTEGER NOT NULL,
    dealer_upcard_val   INTEGER NOT NULL,
    is_soft             INTEGER NOT NULL,
    is_pair             INTEGER NOT NULL,
    pair_card_value     INTEGER NOT NULL DEFAULT 0,
    hand_cards          TEXT    NOT NULL,
    action_taken        TEXT    NOT NULL,
    optimal_action      TEXT    NOT NULL,
    is_correct          INTEGER NOT NULL,
    ml_error_prob       REAL,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_moves_round      ON moves(round_id);
CREATE INDEX IF NOT EXISTS idx_moves_correct    ON moves(is_correct);
CREATE INDEX IF NOT EXISTS idx_moves_situation  ON moves(player_total, dealer_upcard_val, is_soft, is_pair);
CREATE INDEX IF NOT EXISTS idx_rounds_session   ON rounds(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_player  ON sessions(player_id);
"""
