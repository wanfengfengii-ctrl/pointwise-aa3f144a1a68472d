import sqlite3

from handover.receipts import SealReceipt, insert_receipt
from jobs.lifecycle import complete_order, require_pending_order
from packages.contacts import ContactPackage, build_segment_contacts
from packages.store import insert_package
from survey.catalog import require_available_revision


def publish(connection: sqlite3.Connection, order_id: int) -> SealReceipt:
    """Seal the pinned revisions inside the desk's active write transaction."""
    comparison = require_pending_order(connection, order_id)
    a = require_available_revision(connection, comparison.a_revision_id)
    b = require_available_revision(connection, comparison.b_revision_id)
    package = ContactPackage(
        order_id=comparison.order_id,
        a_revision_id=a.revision_id,
        b_revision_id=b.revision_id,
        a_bounds=(a.vertices[0].station, a.vertices[-1].station),
        b_bounds=(b.vertices[0].station, b.vertices[-1].station),
        a_segment_count=len(a.vertices) - 1,
        b_segment_count=len(b.vertices) - 1,
        contacts=build_segment_contacts(a, b),
    )
    package_id = insert_package(connection, package)
    receipt = insert_receipt(connection, package_id, comparison.order_id)
    complete_order(connection, comparison.order_id, receipt.receipt_id)
    return receipt
