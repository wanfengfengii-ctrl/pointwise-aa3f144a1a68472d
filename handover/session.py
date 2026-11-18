from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Iterator

from handover.bundles import ensure_pickup_schema
from handover.receipts import ensure_receipt_schema
from jobs.store import ensure_order_schema
from packages.store import ensure_package_schema
from review.store import ensure_report_schema
from survey.catalog import ensure_revision_schema


def open_database(path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path, isolation_level=None)
    try:
        connection.execute('PRAGMA foreign_keys = ON')
        connection.execute('PRAGMA temp_store = MEMORY')
    except BaseException:
        connection.close()
        raise
    return connection


@contextmanager
def write_transaction(connection: sqlite3.Connection) -> Iterator[None]:
    connection.execute('BEGIN IMMEDIATE')
    try:
        yield
        connection.commit()
    except BaseException:
        if connection.in_transaction:
            connection.rollback()
        raise


def initialize_database(connection: sqlite3.Connection) -> None:
    with write_transaction(connection):
        ensure_revision_schema(connection)
        ensure_order_schema(connection)
        ensure_package_schema(connection)
        ensure_receipt_schema(connection)
        ensure_report_schema(connection)
        ensure_pickup_schema(connection)
