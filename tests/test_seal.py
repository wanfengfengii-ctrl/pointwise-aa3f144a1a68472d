from fractions import Fraction
import json
import sqlite3

from jobs.orders import OrderState
from jobs.store import load_order
from survey.catalog import load_revision
from survey.revisions import RevisionStatus
from tests.support import DeskCase, evidence_rows, fail_at_commit


class SealTests(DeskCase):
    def test_crossing(self):
        a, b, receipt = self.seal([(0, 0, 0), (1, 1, 1)], [(0, 1, 0), (1, 0, 1)])
        package = self.desk.get_package(receipt.package_id)
        half = Fraction(1, 2)
        self.assertEqual((package.a_revision_id, package.b_revision_id), (a, b))
        self.assertEqual(evidence_rows(package), [(1, 1, (half, half), (half, half))])
        self.assertEqual(package.contacts[0].start.xy, (half, half))
        self.assertTrue(package.contacts[0].is_point)
        self.assertEqual(self.desk.get_receipt(receipt.receipt_id), receipt)
        order = load_order(self.connection, receipt.order_id)
        self.assertEqual((order.state, order.receipt_id), (OrderState.SEALED, receipt.receipt_id))

    def test_return_passes(self):
        a, b, receipt = self.seal()
        self.stop_sources(a, b)
        package = self.desk.get_package(receipt.package_id)
        self.assertEqual((package.a_bounds, package.b_bounds), ((0, 8), (0, 2)))
        self.assertEqual((package.a_segment_count, package.b_segment_count), (2, 2))
        self.assertEqual(evidence_rows(package), [
            (1, 1, (2, 1), (3, 0)), (1, 2, (1, 2), (2, 1)),
            (2, 1, (5, 0), (6, 1)), (2, 2, (6, 1), (7, 2)),
        ])
        self.assertFalse(any(contact.is_point for contact in package.contacts))
        self.assertEqual(package.contacts[0].start.xy, package.contacts[2].end.xy)
        self.assertEqual(package.contacts[0].end.xy, package.contacts[2].start.xy)

    def test_rational_codec(self):
        _, _, receipt = self.seal([(0, 0, 0), (1, 1, 1)], [(0, 1, 0), (1, -1, 1)])
        self.reopen()
        third = Fraction(1, 3)
        package = self.desk.get_package(receipt.package_id)
        self.assertEqual(evidence_rows(package), [(1, 1, (third, third), (third, third))])
        self.assertEqual(package.contacts[0].end.xy, (third, third))
        stored = self.connection.execute('SELECT payload FROM packages').fetchone()[0]
        self.assertEqual(json.loads(stored)['contacts'][0][2], ['1/3'] * 4)

    def test_package_read_errors(self):
        _, _, receipt = self.seal()
        with self.assertRaisesRegex(LookupError, 'unknown package'):
            self.desk.get_package(999)
        with self.assertRaisesRegex(LookupError, 'unknown receipt'):
            self.desk.get_receipt(999)
        sql = 'UPDATE packages SET payload = ? WHERE package_id = ?'
        encoded = self.connection.execute('SELECT payload FROM packages').fetchone()[0]
        identity = json.loads(encoded)
        identity['b_revision_id'] = identity['a_revision_id']
        wrong_range = json.loads(encoded)
        wrong_range['a_bounds'] = ['4', '8']
        repeated_pair = json.loads(encoded)
        repeated_pair['contacts'].insert(0, repeated_pair['contacts'][0])
        wrong_endpoint = json.loads(encoded)
        wrong_endpoint['contacts'][0][3][0] = '2'
        unsupported_version = json.loads(encoded)
        unsupported_version['version'] = 2
        for payload in ('{', *map(json.dumps, (identity, wrong_range, repeated_pair,
                                                wrong_endpoint, unsupported_version))):
            with self.subTest(payload=payload):
                self.connection.execute(sql, (payload, receipt.package_id))
                with self.assertRaisesRegex(ValueError, 'invalid package'):
                    self.desk.get_package(receipt.package_id)
        self.connection.execute(sql, (encoded, receipt.package_id))
        self.assertEqual(len(self.desk.get_package(receipt.package_id).contacts), 4)

    def test_package_requires_receipt(self):
        from packages.store import insert_package
        from dataclasses import replace
        from handover.session import write_transaction

        a, b, receipt = self.seal()
        existing = self.desk.get_package(receipt.package_id)
        pending = self.desk.order(a, b)
        with write_transaction(self.connection):
            staged = insert_package(self.connection, replace(existing, order_id=pending))
        with self.assertRaisesRegex(ValueError, 'no success receipt'):
            self.desk.get_package(staged)

    def test_source_retired_before_publish(self):
        a, b, receipt = self.seal()
        before_package = self.desk.get_package(receipt.package_id)
        pending = self.desk.order(a, b)
        self.desk.retire(b)
        before = self.seal_counts()
        with self.assertRaisesRegex(ValueError, 'retired'):
            self.desk.publish(pending)
        self.assertEqual(self.seal_counts(), before)
        order = load_order(self.connection, pending)
        self.assertEqual((order.state, order.receipt_id), (OrderState.PENDING, None))
        self.assertEqual(self.desk.get_package(receipt.package_id), before_package)
        self.assertEqual(self.desk.get_receipt(receipt.receipt_id), receipt)

    def test_retire_boundary(self):
        a, _, receipt = self.seal()
        package = self.desk.get_package(receipt.package_id)
        self.desk.retire(a)
        self.desk.retire(a)
        with self.assertRaisesRegex(LookupError, 'unknown revision'):
            self.desk.retire(999)
        self.reopen()
        self.assertEqual(load_revision(self.connection, a).status, RevisionStatus.RETIRED)
        self.assertEqual(self.desk.get_package(receipt.package_id), package)

    def test_atomic_receipt(self):
        _, _, pending = self.make_order()
        before = self.seal_counts()
        original_order = load_order(self.connection, pending)
        with fail_at_commit(self.connection, 'publish'):
            with self.assertRaisesRegex(sqlite3.IntegrityError, 'FOREIGN KEY constraint failed'):
                self.desk.publish(pending)
            self.assertFalse(self.connection.in_transaction)
        self.reopen()
        self.assertEqual(self.seal_counts(), before)
        self.assertEqual(load_order(self.connection, pending), original_order)
        with self.assertRaises(LookupError):
            self.desk.get_package(1)
        with self.assertRaises(LookupError):
            self.desk.get_receipt(1)
        receipt = self.desk.publish(pending)
        self.assertEqual(self.seal_counts(), (before[0], before[1] + 1, before[2] + 1))
        self.assertEqual(self.desk.get_receipt(receipt.receipt_id), receipt)
        self.assertEqual(len(self.desk.get_package(receipt.package_id).contacts), 4)
        order = load_order(self.connection, pending)
        self.assertEqual((order.state, order.receipt_id), (OrderState.SEALED, receipt.receipt_id))

    def test_sealed_order(self):
        _, _, receipt = self.seal()
        package = self.desk.get_package(receipt.package_id)
        before = self.seal_counts()
        with self.assertRaisesRegex(ValueError, 'already sealed'):
            self.desk.publish(receipt.order_id)
        self.assertEqual(self.seal_counts(), before)
        self.assertEqual(self.desk.get_package(receipt.package_id), package)
        self.assertEqual(self.desk.get_receipt(receipt.receipt_id), receipt)
