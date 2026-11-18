import sqlite3

from jobs.store import insert_pending_order
from survey.catalog import require_available_revision


def order(connection: sqlite3.Connection, a_revision_id: int, b_revision_id: int) -> int:
    a = require_available_revision(connection, a_revision_id)
    b = require_available_revision(connection, b_revision_id)
    return insert_pending_order(connection, a.revision_id, b.revision_id)
