import sqlite3

from jobs.orders import ComparisonOrder, OrderState
from jobs.store import load_order, update_completed_order


def require_pending_order(connection: sqlite3.Connection, order_id: int) -> ComparisonOrder:
    comparison = load_order(connection, order_id)
    if comparison.state != OrderState.PENDING:
        raise ValueError(f'order {order_id} is already sealed')
    return comparison


def complete_order(connection: sqlite3.Connection, order_id: int, receipt_id: int) -> None:
    update_completed_order(connection, order_id, receipt_id)
