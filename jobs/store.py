import sqlite3

from jobs.orders import ComparisonOrder, OrderState


def ensure_order_schema(connection: sqlite3.Connection) -> None:
    connection.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY,
            a_revision_id INTEGER NOT NULL REFERENCES survey_revisions(revision_id),
            b_revision_id INTEGER NOT NULL REFERENCES survey_revisions(revision_id),
            state TEXT NOT NULL,
            receipt_id INTEGER UNIQUE,
            CHECK ((state = 'pending' AND receipt_id IS NULL) OR
                   (state = 'sealed' AND receipt_id IS NOT NULL)),
            UNIQUE (order_id, a_revision_id, b_revision_id),
            FOREIGN KEY (receipt_id, order_id) REFERENCES seal_receipts(receipt_id, order_id)
        )
    ''')


def insert_pending_order(
    connection: sqlite3.Connection, a_revision_id: int, b_revision_id: int
) -> int:
    cursor = connection.execute('''
        INSERT INTO orders (a_revision_id, b_revision_id, state) VALUES (?, ?, 'pending')
    ''', (a_revision_id, b_revision_id))
    return cursor.lastrowid


def load_order(connection: sqlite3.Connection, order_id: int) -> ComparisonOrder:
    if type(order_id) is not int or order_id <= 0:
        raise ValueError('order number must be a positive integer')
    row = connection.execute('''
        SELECT a_revision_id, b_revision_id, state, receipt_id FROM orders WHERE order_id = ?
    ''', (order_id,)).fetchone()
    if row is None:
        raise LookupError(f'unknown order {order_id}')
    a_revision_id, b_revision_id, state, receipt_id = row
    return ComparisonOrder(order_id, a_revision_id, b_revision_id, OrderState(state), receipt_id)


def update_completed_order(connection: sqlite3.Connection, order_id: int, receipt_id: int) -> None:
    cursor = connection.execute('''
        UPDATE orders SET state = 'sealed', receipt_id = ?
        WHERE order_id = ? AND state = 'pending'
    ''', (receipt_id, order_id))
    if cursor.rowcount != 1:
        raise ValueError(f'order {order_id} is not pending')
