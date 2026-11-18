import sqlite3

from survey.revisions import (
    RevisionStatus,
    SurveyRevision,
    decode_revision_vertices,
    encode_revision_vertices,
)
from survey.vertices import Vertex


def ensure_revision_schema(connection: sqlite3.Connection) -> None:
    connection.execute('''
        CREATE TABLE IF NOT EXISTS survey_revisions (
            revision_id INTEGER PRIMARY KEY,
            line_code TEXT NOT NULL,
            ordinal INTEGER NOT NULL CHECK (ordinal > 0),
            status TEXT NOT NULL CHECK (status IN ('available', 'retired')),
            vertices TEXT NOT NULL,
            UNIQUE (line_code, ordinal)
        )
    ''')


def insert_revision(
    connection: sqlite3.Connection, line_code: str, vertices: tuple[Vertex, ...]
) -> int:
    cursor = connection.execute('''
        INSERT INTO survey_revisions (line_code, ordinal, status, vertices)
        SELECT ?, COALESCE(MAX(ordinal), 0) + 1, 'available', ?
        FROM survey_revisions WHERE line_code = ?
    ''', (line_code, encode_revision_vertices(vertices), line_code))
    return cursor.lastrowid


def load_revision(connection: sqlite3.Connection, revision_id: int) -> SurveyRevision:
    if type(revision_id) is not int or revision_id <= 0:
        raise ValueError('revision number must be a positive integer')
    row = connection.execute('''
        SELECT line_code, ordinal, status, vertices
        FROM survey_revisions WHERE revision_id = ?
    ''', (revision_id,)).fetchone()
    if row is None:
        raise LookupError(f'unknown revision {revision_id}')
    line_code, ordinal, status, payload = row
    return SurveyRevision(
        revision_id, line_code, ordinal, RevisionStatus(status), decode_revision_vertices(payload)
    )


def require_available_revision(
    connection: sqlite3.Connection, revision_id: int
) -> SurveyRevision:
    revision = load_revision(connection, revision_id)
    if revision.status == RevisionStatus.RETIRED:
        raise ValueError(f'revision {revision_id} is retired')
    return revision


def mark_retired(connection: sqlite3.Connection, revision_id: int) -> None:
    if type(revision_id) is not int or revision_id <= 0:
        raise ValueError('revision number must be a positive integer')
    cursor = connection.execute('''
        UPDATE survey_revisions SET status = 'retired' WHERE revision_id = ?
    ''', (revision_id,))
    if cursor.rowcount != 1:
        raise LookupError(f'unknown revision {revision_id}')
