"""
SQLite-backed state for sessions, config, and game stats.
Use :memory: for in-memory DB (single connection).
"""
import json
import sqlite3
import time
from typing import Any, Optional

# In-memory by default; use a file path for persistence later.
DB_PATH = ":memory:"

_conn: Optional[sqlite3.Connection] = None


def get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
    return _conn


def init_db() -> None:
    """Create tables and seed default config and game_stats."""
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS config (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            max_rounds INTEGER NOT NULL DEFAULT 5,
            max_sessions INTEGER NOT NULL DEFAULT 10,
            session_timeout_seconds INTEGER NOT NULL DEFAULT 0
        );
        INSERT OR IGNORE INTO config (id, max_rounds, max_sessions, session_timeout_seconds)
        VALUES (1, 5, 10, 0);

        CREATE TABLE IF NOT EXISTS game_stats (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            total_sessions_created INTEGER NOT NULL DEFAULT 0,
            total_matches_completed INTEGER NOT NULL DEFAULT 0,
            total_rounds_played INTEGER NOT NULL DEFAULT 0,
            player_wins INTEGER NOT NULL DEFAULT 0,
            server_wins INTEGER NOT NULL DEFAULT 0,
            draws INTEGER NOT NULL DEFAULT 0
        );
        INSERT OR IGNORE INTO game_stats (id) VALUES (1);

        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id TEXT,
            max_rounds INTEGER NOT NULL,
            round_number INTEGER NOT NULL DEFAULT 0,
            player_score INTEGER NOT NULL DEFAULT 0,
            server_score INTEGER NOT NULL DEFAULT 0,
            winner TEXT,
            created_at REAL NOT NULL,
            last_activity_at REAL NOT NULL,
            round_history TEXT NOT NULL DEFAULT '[]'
        );
    """)
    conn.commit()


def get_config() -> dict[str, Any]:
    conn = get_conn()
    row = conn.execute(
        "SELECT max_rounds, max_sessions, session_timeout_seconds FROM config WHERE id = 1"
    ).fetchone()
    if not row:
        return {"max_rounds": 5, "max_sessions": 10, "session_timeout_seconds": 0}
    return {
        "max_rounds": row["max_rounds"],
        "max_sessions": row["max_sessions"],
        "session_timeout_seconds": row["session_timeout_seconds"],
    }


def set_config(max_rounds: Optional[int] = None, max_sessions: Optional[int] = None, session_timeout_seconds: Optional[int] = None) -> None:
    conn = get_conn()
    updates = []
    params = []
    if max_rounds is not None:
        updates.append("max_rounds = ?")
        params.append(max_rounds)
    if max_sessions is not None:
        updates.append("max_sessions = ?")
        params.append(max_sessions)
    if session_timeout_seconds is not None:
        updates.append("session_timeout_seconds = ?")
        params.append(session_timeout_seconds)
    if updates:
        params.append(1)
        conn.execute(f"UPDATE config SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()


def _row_to_session(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "user_id": row["user_id"],
        "max_rounds": row["max_rounds"],
        "round_number": row["round_number"],
        "player_score": row["player_score"],
        "server_score": row["server_score"],
        "winner": row["winner"],
        "created_at": row["created_at"],
        "last_activity_at": row["last_activity_at"],
        "round_history": json.loads(row["round_history"] or "[]"),
    }


def get_session(session_id: str) -> Optional[dict[str, Any]]:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
    ).fetchone()
    if not row:
        return None
    state = _row_to_session(row)
    state["session_id"] = row["session_id"]
    return state


def list_sessions() -> list[tuple[str, dict[str, Any]]]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM sessions").fetchall()
    return [(row["session_id"], _row_to_session(row)) for row in rows]


def create_session(
    session_id: str,
    user_id: Optional[str],
    max_rounds: int,
    created_at: float,
    last_activity_at: float,
) -> None:
    conn = get_conn()
    conn.execute(
        """INSERT INTO sessions (session_id, user_id, max_rounds, round_number, player_score, server_score, winner, created_at, last_activity_at, round_history)
           VALUES (?, ?, ?, 0, 0, 0, NULL, ?, ?, '[]')""",
        (session_id, user_id, max_rounds, created_at, last_activity_at),
    )
    conn.execute(
        "UPDATE game_stats SET total_sessions_created = total_sessions_created + 1 WHERE id = 1"
    )
    conn.commit()


def update_session_after_play(
    session_id: str,
    round_number: int,
    player_score: int,
    server_score: int,
    winner: Optional[str],
    round_history: list[dict],
    last_activity_at: float,
) -> None:
    conn = get_conn()
    conn.execute(
        """UPDATE sessions SET round_number = ?, player_score = ?, server_score = ?, winner = ?, round_history = ?, last_activity_at = ?
           WHERE session_id = ?""",
        (round_number, player_score, server_score, winner, json.dumps(round_history), last_activity_at, session_id),
    )
    conn.execute(
        "UPDATE game_stats SET total_rounds_played = total_rounds_played + 1 WHERE id = 1"
    )
    conn.commit()


def record_match_result(winner: str) -> None:
    """winner is 'player', 'server', or 'draw'."""
    conn = get_conn()
    conn.execute(
        "UPDATE game_stats SET total_matches_completed = total_matches_completed + 1 WHERE id = 1"
    )
    if winner == "player":
        conn.execute("UPDATE game_stats SET player_wins = player_wins + 1 WHERE id = 1")
    elif winner == "server":
        conn.execute("UPDATE game_stats SET server_wins = server_wins + 1 WHERE id = 1")
    else:
        conn.execute("UPDATE game_stats SET draws = draws + 1 WHERE id = 1")
    conn.commit()


def delete_session(session_id: str) -> None:
    conn = get_conn()
    conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    conn.commit()


def count_sessions() -> int:
    conn = get_conn()
    row = conn.execute("SELECT COUNT(*) AS n FROM sessions").fetchone()
    return row["n"] if row else 0


def get_effective_session_timeout_seconds() -> int:
    """Session expiry in seconds. When config.session_timeout_seconds is 0, returns 30 * max_rounds."""
    cfg = get_config()
    timeout = cfg.get("session_timeout_seconds") or 0
    if timeout > 0:
        return timeout
    return 30 * (cfg.get("max_rounds") or 5)


def evict_expired_sessions() -> None:
    """Delete sessions that have exceeded the effective session timeout (30 * max_rounds when config is 0)."""
    timeout = get_effective_session_timeout_seconds()
    if timeout <= 0:
        return
    now = time.time()
    conn = get_conn()
    rows = conn.execute(
        "SELECT session_id, last_activity_at, created_at FROM sessions"
    ).fetchall()
    for row in rows:
        last = row["last_activity_at"] or row["created_at"] or 0
        if (now - last) > timeout:
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (row["session_id"],))
    conn.commit()


def get_game_stats() -> dict[str, int]:
    conn = get_conn()
    row = conn.execute(
        """SELECT total_sessions_created, total_matches_completed, total_rounds_played,
                  player_wins, server_wins, draws FROM game_stats WHERE id = 1"""
    ).fetchone()
    if not row:
        return {
            "total_sessions_created": 0,
            "total_matches_completed": 0,
            "total_rounds_played": 0,
            "player_wins": 0,
            "server_wins": 0,
            "draws": 0,
        }
    return dict(row)
