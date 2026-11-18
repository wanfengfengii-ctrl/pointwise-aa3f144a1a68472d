from fractions import Fraction

from handover.bundles import load_report_pickup
from jobs.store import load_order
from survey.catalog import load_revision
from survey.revisions import RevisionStatus
from tests.support import DeskCase, report_rows


class HistoryTests(DeskCase):
    def test_reopen_after_correction(self):
        a, b, receipt = self.seal()
        report = self.desk.issue(receipt.package_id, 2, 6)
        package = self.desk.get_package(receipt.package_id)
        original_order = load_order(self.connection, receipt.order_id)
        self.desk.retire(a)
        corrected = self.desk.register('A', [(0, 2, 0), (4, 2, 4)])
        self.reopen()
        self.desk.initialize()
        self.desk.initialize()
        self.assertEqual(load_revision(self.connection, a).status, RevisionStatus.RETIRED)
        self.assertEqual(load_revision(self.connection, corrected).ordinal, 2)
        with self.assertRaisesRegex(ValueError, 'retired'):
            self.desk.order(a, b)
        corrected_order = self.desk.order(corrected, b)
        new_receipt = self.desk.publish(corrected_order)
        self.assertEqual(self.desk.get_package(new_receipt.package_id).contacts, ())
        self.assertEqual(load_order(self.connection, receipt.order_id), original_order)
        self.assertEqual(self.desk.get_package(receipt.package_id), package)
        self.assertEqual(self.desk.get_report(report.report_id), report)
        self.assertEqual(self.desk.get_receipt(receipt.receipt_id), receipt)

    def test_report_number(self):
        a, b, receipt = self.seal()
        first = self.desk.issue(receipt.package_id, 2, 6)
        second = self.desk.issue(receipt.package_id, '3/2', '3/2')
        self.assertNotEqual(first.report_id, second.report_id)
        self.assertEqual(report_rows(first), [('reverse', (2, 1), (3, 0)), ('same', (5, 0), (6, 1))])
        point = (Fraction(3, 2), Fraction(3, 2))
        self.assertEqual(report_rows(second), [('point', point, point)])
        self.stop_sources(a, b)
        self.desk.register('B', [(3, 4, 0), (1, 4, 2)])
        self.reopen()
        self.desk.initialize()
        for report in (first, second, first):
            self.assertEqual(self.desk.get_report(report.report_id), report)
            pickup = load_report_pickup(self.connection, report.report_id)
            self.assertEqual((pickup.package_id, pickup.receipt_id), (receipt.package_id, receipt.receipt_id))
        self.assertEqual(self.desk.get_receipt(receipt.receipt_id), receipt)
        with self.assertRaisesRegex(LookupError, 'unknown report'):
            self.desk.get_report(999)
