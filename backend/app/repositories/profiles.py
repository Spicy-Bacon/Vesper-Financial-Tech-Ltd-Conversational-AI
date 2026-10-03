import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from ..schemas import Profile


class ProfileRepository:
    """Session changes, retry cache and accepted profiles share one transaction."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY, state TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS requests (
                    session_id TEXT NOT NULL, request_id TEXT NOT NULL,
                    fingerprint TEXT NOT NULL, response TEXT NOT NULL,
                    PRIMARY KEY (session_id, request_id),
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                );
                CREATE TABLE IF NOT EXISTS profiles (
                    id TEXT PRIMARY KEY, session_id TEXT NOT NULL,
                    version INTEGER NOT NULL, document TEXT NOT NULL,
                    UNIQUE (session_id, version),
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                );
                CREATE TABLE IF NOT EXISTS v1_creations (
                    request_id TEXT PRIMARY KEY, session_id TEXT NOT NULL UNIQUE,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                );
            """)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        try:
            yield db
        finally:
            db.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise

    def load_session(self, db: sqlite3.Connection, session_id: str) -> dict | None:
        row = db.execute("SELECT state FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return json.loads(row["state"]) if row else None

    def creation_session(self, db: sqlite3.Connection, request_id: str) -> str | None:
        row = db.execute(
            "SELECT session_id FROM v1_creations WHERE request_id = ?", (request_id,),
        ).fetchone()
        return row["session_id"] if row else None

    def store_creation(self, db: sqlite3.Connection, request_id: str, session_id: str) -> None:
        db.execute(
            "INSERT INTO v1_creations (request_id, session_id) VALUES (?, ?)",
            (request_id, session_id),
        )

    def store_session(self, db: sqlite3.Connection, session_id: str, state: dict) -> None:
        db.execute(
            "INSERT INTO sessions (id, state) VALUES (?, ?) "
            "ON CONFLICT(id) DO UPDATE SET state = excluded.state",
            (session_id, json.dumps(state)),
        )

    def cached_request(self, db: sqlite3.Connection, session_id: str, request_id: str):
        return db.execute(
            "SELECT fingerprint, response FROM requests WHERE session_id = ? AND request_id = ?",
            (session_id, request_id),
        ).fetchone()

    def store_request(self, db: sqlite3.Connection, session_id: str, request_id: str,
                      fingerprint: str, response: str) -> None:
        db.execute(
            "INSERT INTO requests (session_id, request_id, fingerprint, response) VALUES (?, ?, ?, ?)",
            (session_id, request_id, fingerprint, response),
        )

    def save(self, db: sqlite3.Connection, profile: Profile) -> None:
        db.execute(
            "INSERT INTO profiles (id, session_id, version, document) VALUES (?, ?, ?, ?)",
            (profile.id, profile.sessionId, profile.version, profile.model_dump_json()),
        )

    def list_for_session(self, session_id: str) -> list[Profile]:
        """Internal access only; no unauthenticated profile-read HTTP route."""
        with self._connection() as db:
            rows = db.execute(
                "SELECT document FROM profiles WHERE session_id = ? ORDER BY version", (session_id,),
            ).fetchall()
        return [Profile.model_validate_json(row["document"]) for row in rows]
