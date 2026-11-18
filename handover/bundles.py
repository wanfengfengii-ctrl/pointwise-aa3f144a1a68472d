from dataclasses import dataclass
import sqlite3

from handover.receipts import load_receipt_by_package
from packages.contacts import ContactPackage
from packages.store import load_package


@dataclass(frozen=True, slots=True)
class ReportPickup:
    report_id: int
    package_id: int
    receipt_id: int


def ensure_pickup_schema(connection: sqlite3.Connection) -> None:
    connection.execute('''
        CREATE TABLE IF NOT EXISTS report_pickups (
            report_id INTEGER PRIMARY KEY,
            package_id INTEGER NOT NULL,
            receipt_id INTEGER NOT NULL,
            FOREIGN KEY (report_id, package_id) REFERENCES reports(report_id, package_id),
            FOREIGN KEY (receipt_id, package_id) REFERENCES seal_receipts(receipt_id, package_id)
        )
    ''')


def get_package(connection: sqlite3.Connection, package_id: int) -> ContactPackage:
    package = load_package(connection, package_id)
    try:
        receipt = load_receipt_by_package(connection, package_id)
    except LookupError as error:
        raise ValueError(f'package {package_id} has no success receipt') from error
    if receipt.order_id != package.order_id:
        raise ValueError(f'package {package_id} and receipt disagree on order')
    return package


def bind_report_pickup(
    connection: sqlite3.Connection, report_id: int, package_id: int
) -> ReportPickup:
    receipt = load_receipt_by_package(connection, package_id)
    connection.execute('''
        INSERT INTO report_pickups (report_id, package_id, receipt_id) VALUES (?, ?, ?)
    ''', (report_id, package_id, receipt.receipt_id))
    return ReportPickup(report_id, package_id, receipt.receipt_id)


def load_report_pickup(connection: sqlite3.Connection, report_id: int) -> ReportPickup:
    row = connection.execute('''
        SELECT report_id, package_id, receipt_id FROM report_pickups WHERE report_id = ?
    ''', (report_id,)).fetchone()
    if row is None:
        raise LookupError(f'no pickup for report {report_id}')
    return ReportPickup(*row)
