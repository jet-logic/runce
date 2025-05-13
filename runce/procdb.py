import sqlite3
from pathlib import Path
from .spawn import Spawn


class ProcessDB(Spawn):
    """SQLite database for RunCE process tracking."""

    db_path: Path

    def _get_db_path(self):
        dd = self.data_dir
        dd.mkdir(parents=True, exist_ok=True)
        db = dd / "db"
        """Initialize the database schema."""
        with sqlite3.connect(db) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS processes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uuid TEXT NOT NULL UNIQUE, 
                    pid INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    cmd TEXT NOT NULL,  -- JSON-encoded list
                    out TEXT,
                    err TEXT,
                    started REAL NOT NULL,
                    is_active INTEGER DEFAULT 1
                )
            """
            )
        return db

    def connect(self):
        return sqlite3.connect(self.db_path)

    def add_process(
        self,
        process_info: dict[str, object],
    ):
        """Insert a new process record."""
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO processes (
                    uuid, pid, name, cmd, out, err, started
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    process_info["uuid"],
                    process_info["pid"],
                    process_info["name"],
                    str(process_info["cmd"]),  # Store cmd as JSON string
                    process_info["out"],
                    process_info["err"],
                    process_info["started"],
                ),
            )
        x = self.find_uuid(process_info["uuid"])
        assert x
        return x

    def all(self):
        """List all active processes."""
        with self.connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM processes")
            for row in cursor.fetchall():
                # id ,  uuid , pid , name, cmd,  out , err , started,  is_active
                yield {
                    "id": row["id"],
                    "uuid": row["uuid"],
                    "pid": row["pid"],
                    "name": row["name"],
                    "cmd": eval(row["cmd"]),
                    "out": row["out"],
                    "err": row["err"],
                    "started": row["started"],
                }

    def find_uuid(self, uuid: str):
        """Find a process by uuid"""
        with self.connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM processes WHERE uuid = ? ", (uuid,))
            for row in cursor.fetchall():
                return {
                    "id": row["id"],
                    "uuid": row["uuid"],
                    "pid": row["pid"],
                    "name": row["name"],
                    "cmd": eval(row["cmd"]),
                    "out": row["out"],
                    "err": row["err"],
                    "started": row["started"],
                }

    def drop(self, entry: dict[str, object], clean_up=True):
        with self.connect() as conn:
            conn.cursor().execute(
                "DELETE FROM processes WHERE uuid = ?", (entry["uuid"],)
            )
            # print(f"Row with ID {entry["id"]} deleted successfully. {entry["name"]}")
        super().drop(entry, clean_up)
        assert self.find_uuid(entry["uuid"]) is None
