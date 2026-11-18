import sqlite3

from packages.codec import decode_package, encode_package
from packages.contacts import ContactPackage


def ensure_package_schema(connection: sqlite3.Connection) -> None:
    connection.execute('''
        CREATE TABLE IF NOT EXISTS packages (
            package_id INTEGER PRIMARY KEY,
            order_id INTEGER NOT NULL UNIQUE,
            a_revision_id INTEGER NOT NULL,
            b_revision_id INTEGER NOT NULL,
            payload TEXT NOT NULL,
            UNIQUE (package_id, order_id),
            FOREIGN KEY (order_id, a_revision_id, b_revision_id)
                REFERENCES orders(order_id, a_revision_id, b_revision_id)
        )
    ''')


def insert_package(connection: sqlite3.Connection, package: ContactPackage) -> int:
    cursor = connection.execute('''
        INSERT INTO packages (order_id, a_revision_id, b_revision_id, payload) VALUES (?, ?, ?, ?)
    ''', (package.order_id, package.a_revision_id, package.b_revision_id, encode_package(package)))
    return cursor.lastrowid


def load_package(connection: sqlite3.Connection, package_id: int) -> ContactPackage:
    if type(package_id) is not int or package_id <= 0:
        raise ValueError('package number must be a positive integer')
    row = connection.execute('''
        SELECT order_id, a_revision_id, b_revision_id, payload
        FROM packages WHERE package_id = ?
    ''', (package_id,)).fetchone()
    if row is None:
        raise LookupError(f'unknown package {package_id}')
    try:
        package = decode_package(row[3])
        if (package.order_id, package.a_revision_id, package.b_revision_id) != row[:3]:
            raise ValueError('stored package identity disagrees with payload')
    except (ValueError, TypeError) as error:
        raise ValueError(f'invalid package {package_id}: {error}') from error
    return package
