import sqlite3

from handover.bundles import get_package, load_report_pickup
from handover.receipts import load_receipt
from review.store import WindowReport, load_report


def get_report(connection: sqlite3.Connection, report_id: int) -> WindowReport:
    report = load_report(connection, report_id)
    try:
        pickup = load_report_pickup(connection, report_id)
        receipt = load_receipt(connection, pickup.receipt_id)
        package = get_package(connection, report.package_id)
    except LookupError as error:
        raise ValueError(f'report {report_id} has an incomplete pickup') from error
    if pickup.package_id != report.package_id or receipt.package_id != report.package_id:
        raise ValueError(f'report {report_id} has an inconsistent pickup')
    if receipt.order_id != package.order_id:
        raise ValueError(f'report {report_id} has an inconsistent receipt')
    if not package.a_bounds[0] <= report.window.left <= report.window.right <= package.a_bounds[1]:
        raise ValueError(f'report {report_id} is outside its package range')
    return report
