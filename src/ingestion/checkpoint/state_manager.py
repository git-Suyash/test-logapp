import sqlite3
import time
from pathlib import Path


class StateManager:

    def __init__(self, db_path="data/checkpoints/scanner_state.db"):

        Path("data/checkpoints").mkdir(parents=True, exist_ok=True)

        self.db_path = db_path

        self._init_db()

    def _init_db(self):

        with sqlite3.connect(self.db_path) as conn:

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS file_state (
                    inode INTEGER PRIMARY KEY,
                    filename TEXT,
                    byte_offset BIGINT,
                    last_timestamp REAL
                )
                """
            )

            conn.commit()

    def get_offset(self, inode):

        with sqlite3.connect(self.db_path) as conn:

            cursor = conn.cursor()

            cursor.execute(
                "SELECT byte_offset FROM file_state WHERE inode = ?",
                (inode,)
            )

            row = cursor.fetchone()

            return row[0] if row else 0

    def save_state(self, inode, filename, offset):

        with sqlite3.connect(self.db_path) as conn:

            conn.execute(
                """
                INSERT INTO file_state (
                    inode,
                    filename,
                    byte_offset,
                    last_timestamp
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(inode) DO UPDATE SET
                    filename = excluded.filename,
                    byte_offset = excluded.byte_offset,
                    last_timestamp = excluded.last_timestamp
                """,
                (inode, filename, offset, time.time())
            )

            conn.commit()
