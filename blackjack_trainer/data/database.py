from __future__ import annotations
import sqlite3
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from data.schema import SCHEMA_SQL

_DEFAULT_PATH = Path(__file__).parent.parent / "blackjack.db"


class Database:
    """Thin wrapper around sqlite3. Keeps a single connection for the whole app."""

    def __init__(self, db_path: str | Path = _DEFAULT_PATH):
        self.db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            str(self.db_path),
            detect_types=sqlite3.PARSE_DECLTYPES,
            check_same_thread=False,  # Streamlit runs multiple threads
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = self._connect()
        return self._conn

    @contextmanager
    def cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        conn = self.get_conn()
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def _init_db(self) -> None:
        """Create all tables on first run."""
        conn = self.get_conn()
        conn.executescript(SCHEMA_SQL)
        conn.commit()

    @staticmethod
    def to_json(value: list | dict) -> str:
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def from_json(value: str) -> list | dict:
        return json.loads(value)
