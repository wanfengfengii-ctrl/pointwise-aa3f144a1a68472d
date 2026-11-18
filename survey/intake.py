import sqlite3

from survey.catalog import insert_revision, mark_retired
from survey.vertices import parse_vertices


def register(connection: sqlite3.Connection, line_code: str, records) -> int:
    if not isinstance(line_code, str) or not line_code.strip():
        raise ValueError('survey line code must be non-empty')
    return insert_revision(connection, line_code, parse_vertices(records))


def retire(connection: sqlite3.Connection, revision_id: int) -> None:
    mark_retired(connection, revision_id)
