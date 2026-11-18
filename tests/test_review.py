from dataclasses import replace
from fractions import Fraction
from pathlib import Path
import sqlite3

from handover.bundles import load_report_pickup
from handover.receipts import insert_receipt
from handover.session import write_transaction
from jobs.lifecycle import complete_order
from packages.codec import decode_package
from packages.store import insert_package
from tests.support import DeskCase, RETURN_A, evidence_rows, fail_at_commit, report_rows


FULL = [('reverse', (1, 2), (3, 0)), ('same', (5, 0), (7, 2))]
SECTION = [('reverse', (2, 1), (3, 0)), ('same', (5, 0), (6, 1))]


class ReviewTests(DeskCase):
    def assert_standard_windows(self, package_id):
        full = self.desk.issue(package_id, 0, 8)
        section = self.desk.issue(package_id, 2, 6)
        self.assertEqual(report_rows(full), FULL)
        self.assertEqual(report_rows(section), SECTION)
        self.assertEqual(self.desk.get_report(full.report_id), full)
        self.assertEqual(self.desk.get_report(section.report_id), section)

    def test_return_and_split(self):
        a, b, receipt = self.seal()
        self.stop_sources(a, b)
        self.reopen()
        package = self.desk.get_package(receipt.package_id)
        self.assertEqual(evidence_rows(package), [
            (1, 1, (2, 1), (3, 0)), (1, 2, (1, 2), (2, 1)),
            (2, 1, (5, 0), (6, 1)), (2, 2, (6, 1), (7, 2)),
        ])
        self.assert_standard_windows(receipt.package_id)

    def test_manual_package(self):
        sample = Path(__file__).resolve().parents[1] / 'samples' / 'manual-package.json'
        manual = decode_package(sample.read_text(encoding='utf-8'))
        a, b, order = self.make_order()
        manual = replace(manual, order_id=order, a_revision_id=a, b_revision_id=b)
        with write_transaction(self.connection):
            package_id = insert_package(self.connection, manual)
            receipt = insert_receipt(self.connection, package_id, order)
            complete_order(self.connection, order, receipt.receipt_id)
        self.stop_sources(a, b)
        self.reopen()
        self.assertEqual(self.desk.get_package(package_id), manual)
        self.assert_standard_windows(package_id)

    def test_dual_station_seam(self):
        a = [(0, 0, 0), (4, 0, 4)]
        b = [(0, 0, 0), (2, 0, 2), (2, 1, 3), (2, 0, 4), (4, 0, 6)]
        a_id, b_id, receipt = self.seal(a, b)
        self.stop_sources(a_id, b_id)
        report = self.desk.issue(receipt.package_id, 0, 4)
        self.assertEqual(report_rows(report), [('same', (0, 0), (2, 2)), ('same', (2, 4), (4, 6))])

    def test_direction_turn(self):
        a, b, receipt = self.seal(RETURN_A, RETURN_A)
        self.stop_sources(a, b)
        report = self.desk.issue(receipt.package_id, 0, 8)
        self.assertEqual(report_rows(report), [('same', (0, 0), (8, 8)), ('reverse', (0, 8), (8, 0))])
        at_turn = self.desk.issue(receipt.package_id, 4, 4)
        self.assertEqual(report_rows(at_turn), [('point', (4, 4), (4, 4))])

    def test_point_coverage(self):
        a = [(-1, 0, 0), (0, 0, 1), (1, 0, 2)]
        cross = [(0, -1, 0), (0, 0, 1), (0, 1, 2)]
        first_a, first_b, first = self.seal(a, cross)
        self.stop_sources(first_a, first_b)
        self.assertEqual(evidence_rows(self.desk.get_package(first.package_id)), [
            (1, 1, (1, 1), (1, 1)), (1, 2, (1, 1), (1, 1)),
            (2, 1, (1, 1), (1, 1)), (2, 2, (1, 1), (1, 1)),
        ])
        self.assertEqual(report_rows(self.desk.issue(first.package_id, 0, 2)),
                         [('point', (1, 1), (1, 1))])
        revisit = [(-1, 0, 0), (0, 0, 1), (0, 1, 2), (0, 0, 3), (0, -1, 4)]
        second_a, second_b, second = self.seal(a, revisit)
        self.stop_sources(second_a, second_b)
        self.assertEqual(report_rows(self.desk.issue(second.package_id, 0, 2)),
                         [('same', (0, 0), (1, 1)), ('point', (1, 3), (1, 3))])

    def test_piecewise_point(self):
        a, b, receipt = self.seal(RETURN_A, [(3, 0, 0), (2, 0, 1), (1, 0, 4)])
        self.stop_sources(a, b)
        whole = self.desk.issue(receipt.package_id, 0, 8)
        self.assertEqual(report_rows(whole), [('reverse', (1, 4), (3, 0)), ('same', (5, 0), (7, 4))])
        report = self.desk.issue(receipt.package_id, '3/2', '3/2')
        point = (Fraction(3, 2), Fraction(5, 2))
        self.assertEqual(report_rows(report), [('point', point, point)])

    def test_rational_breaks(self):
        a, b, receipt = self.seal(RETURN_A, [(3, 0, 0), (2, 0, '1/3'), (1, 0, 4)])
        self.stop_sources(a, b)
        package = self.desk.get_package(receipt.package_id)
        self.assertEqual(package.contacts[1].end.b_station, Fraction(1, 3))
        report = self.desk.issue(receipt.package_id, '3/2', '3/2')
        point = (Fraction(3, 2), Fraction(13, 6))
        self.assertEqual(report_rows(report), [('point', point, point)])
        self.reopen()
        self.assertEqual(self.desk.get_report(report.report_id), report)

    def test_inverted_window(self):
        _, _, receipt = self.seal()
        before = self.issue_counts()
        with self.assertRaisesRegex(ValueError, 'inverted'):
            self.desk.issue(receipt.package_id, 3, 2)
        self.assertEqual(self.issue_counts(), before)
        report = self.desk.issue(receipt.package_id, 2, 3)
        self.assertEqual(report_rows(report), [SECTION[0]])
        self.assertEqual(self.issue_counts(), (before[0] + 1, before[1] + 1))

    def test_window_boundaries(self):
        a, b, receipt = self.seal([(0, 0, 10), (4, 0, 14)], [(0, 0, -3), (4, 0, 1)])
        self.stop_sources(a, b)
        for station, corresponding in ((10, -3), (14, 1)):
            report = self.desk.issue(receipt.package_id, station, station)
            point = (station, corresponding)
            self.assertEqual(report_rows(report), [('point', point, point)])
        before = self.issue_counts()
        for left, right in ((9, 10), (14, 15), (14, '1/0')):
            with self.subTest(left=left, right=right):
                with self.assertRaises(ValueError):
                    self.desk.issue(receipt.package_id, left, right)
        with self.assertRaisesRegex(LookupError, 'unknown package'):
            self.desk.issue(999, 10, 11)
        self.assertEqual(self.issue_counts(), before)

    def test_issue_abort(self):
        a, b, receipt = self.seal()
        self.stop_sources(a, b)
        package = self.desk.get_package(receipt.package_id)
        previous = self.desk.issue(receipt.package_id, 0, 8)
        before = self.issue_counts()
        with fail_at_commit(self.connection, 'issue'):
            with self.assertRaisesRegex(sqlite3.IntegrityError, 'FOREIGN KEY constraint failed'):
                self.desk.issue(receipt.package_id, 2, 6)
            self.assertFalse(self.connection.in_transaction)
        self.reopen()
        self.assertEqual(self.issue_counts(), before)
        self.assertEqual(self.desk.get_package(receipt.package_id), package)
        self.assertEqual(self.desk.get_report(previous.report_id), previous)
        report = self.desk.issue(receipt.package_id, 2, 6)
        self.assertEqual(report_rows(report), SECTION)
        self.assertEqual(self.issue_counts(), (before[0] + 1, before[1] + 1))
        pickup = load_report_pickup(self.connection, report.report_id)
        self.assertEqual((pickup.package_id, pickup.receipt_id), (receipt.package_id, receipt.receipt_id))

    def test_disjoint(self):
        a, b, receipt = self.seal([(0, 0, 2), (4, 0, 6)], [(0, 1, 1), (4, 1, 3)])
        self.stop_sources(a, b)
        package = self.desk.get_package(receipt.package_id)
        self.assertEqual(package.contacts, ())
        self.assertEqual(package.a_bounds, (2, 6))
        report = self.desk.issue(receipt.package_id, 2, 6)
        self.assertEqual(report.contacts, ())
        self.assertEqual(self.desk.get_report(report.report_id), report)
