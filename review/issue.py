import sqlite3

from handover.bundles import bind_report_pickup, get_package
from review.clipping import settle_contacts
from review.continuity import merge_overlaps
from review.store import WindowReport, insert_report
from review.windows import validate_window


def issue(connection: sqlite3.Connection, package_id: int, left, right) -> WindowReport:
    """Sign a fixed-package report and bind its pickup in the active transaction."""
    package = get_package(connection, package_id)
    window = validate_window(left, right, package.a_bounds)
    runs = merge_overlaps(package.contacts)
    contacts = settle_contacts(package.contacts, runs, window)
    report = insert_report(connection, package_id, window, contacts)
    bind_report_pickup(connection, report.report_id, report.package_id)
    return report
