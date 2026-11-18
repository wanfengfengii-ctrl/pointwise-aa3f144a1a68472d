from dataclasses import dataclass
import sqlite3


@dataclass(frozen=True, slots=True)
class SealReceipt:
    receipt_id: int
    package_id: int
    order_id: int


def ensure_receipt_schema(connection: sqlite3.Connection) -> None:
    connection.execute('''
        CREATE TABLE IF NOT EXISTS seal_receipts (
            receipt_id INTEGER PRIMARY KEY,
            package_id INTEGER NOT NULL UNIQUE,
            order_id INTEGER NOT NULL UNIQUE,
            UNIQUE (receipt_id, order_id),
            UNIQUE (receipt_id, package_id),
            FOREIGN KEY (package_id, order_id) REFERENCES packages(package_id, order_id)
        )
    ''')


def insert_receipt(connection: sqlite3.Connection, package_id: int, order_id: int) -> SealReceipt:
    cursor = connection.execute('''
        INSERT INTO seal_receipts (package_id, order_id) VALUES (?, ?)
    ''', (package_id, order_id))
    return SealReceipt(cursor.lastrowid, package_id, order_id)


def load_receipt(connection: sqlite3.Connection, receipt_id: int) -> SealReceipt:
    if type(receipt_id) is not int or receipt_id <= 0:
        raise ValueError('receipt number must be a positive integer')
    row = connection.execute('''
        SELECT receipt_id, package_id, order_id FROM seal_receipts WHERE receipt_id = ?
    ''', (receipt_id,)).fetchone()
    if row is None:
        raise LookupError(f'unknown receipt {receipt_id}')
    return SealReceipt(*row)


def load_receipt_by_package(connection: sqlite3.Connection, package_id: int) -> SealReceipt:
    if type(package_id) is not int or package_id <= 0:
        raise ValueError('package number must be a positive integer')
    row = connection.execute('''
        SELECT receipt_id, package_id, order_id FROM seal_receipts WHERE package_id = ?
    ''', (package_id,)).fetchone()
    if row is None:
        raise LookupError(f'no receipt for package {package_id}')
    return SealReceipt(*row)
