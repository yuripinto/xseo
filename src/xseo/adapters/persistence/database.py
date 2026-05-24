"""SQLite database lifecycle helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from xseo.adapters.persistence.schema import DDL


class SQLiteDatabase:
    def __init__(self, path):
        self.path = str(path)

    @classmethod
    def memory(cls):
        return cls(":memory:")

    def connect(self):
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(DDL)
        return connection

    def initialize(self):
        with self.connect():
            pass
        return self


def sqlite_database(path):
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    return SQLiteDatabase(path).initialize()
