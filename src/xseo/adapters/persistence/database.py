"""SQLite database lifecycle helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from xseo.adapters.persistence.schema import DDL, PAGE_COLUMN_MIGRATIONS


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
        _apply_column_migrations(connection)
        return connection

    def initialize(self):
        with self.connect():
            pass
        return self


def _apply_column_migrations(connection):
    existing = {row["name"] for row in connection.execute("PRAGMA table_info(pages)")}
    for column, statement in PAGE_COLUMN_MIGRATIONS:
        if column not in existing:
            connection.execute(statement)
    connection.commit()


def sqlite_database(path):
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    return SQLiteDatabase(path).initialize()
