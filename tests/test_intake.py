from fractions import Fraction

from jobs.orders import OrderState
from jobs.store import load_order
from survey.catalog import load_revision
from survey.revisions import RevisionStatus
from tests.support import DeskCase, RETURN_A, SPLIT_B


class IntakeTests(DeskCase):
    def test_equal_station(self):
        a = self.desk.register('A', RETURN_A)
        before = load_revision(self.connection, a)
        with self.assertRaisesRegex(ValueError, 'strictly increase'):
            self.desk.register('A', [(0, 0, 0), (1, 0, 0)])
        self.assertEqual(self.revision_count(), 1)
        self.assertEqual(load_revision(self.connection, a), before)
        b = self.desk.register('B', SPLIT_B)
        saved = load_order(self.connection, self.desk.order(a, b))
        self.assertEqual((saved.a_revision_id, saved.b_revision_id), (a, b))

    def test_pinned_order(self):
        a = self.desk.register('A', RETURN_A)
        old = load_revision(self.connection, a)
        with self.assertRaisesRegex(ValueError, 'strictly increase'):
            self.desk.register('A', [(1, 1, 2), (1, 2, 1)])
        newer = self.desk.register('A', [('1/3', 0, '-7/2'), ('5/3', 0, '5/2')])
        b = self.desk.register('B', SPLIT_B)
        first = load_order(self.connection, self.desk.order(a, b))
        second = load_order(self.connection, self.desk.order(newer, b))
        self.assertEqual((first.a_revision_id, first.b_revision_id), (a, b))
        self.assertEqual((second.a_revision_id, second.b_revision_id), (newer, b))
        self.assertEqual(first.state, OrderState.PENDING)
        self.assertEqual(load_revision(self.connection, a), old)
        revision = load_revision(self.connection, newer)
        self.assertEqual((revision.line_code, revision.ordinal, revision.status),
                         ('A', 2, RevisionStatus.AVAILABLE))
        self.assertEqual(revision.vertices[0].x, Fraction(1, 3))
        self.assertEqual(revision.vertices[0].station, Fraction(-7, 2))
        self.assertEqual(self.revision_count(), 3)
        receipt = self.desk.publish(first.order_id)
        self.assertEqual(self.desk.get_package(receipt.package_id).a_revision_id, a)

    def test_unavailable_order(self):
        a, b, existing = self.make_order()
        before = self.seal_counts()
        self.desk.retire(b)
        with self.assertRaisesRegex(ValueError, 'retired'):
            self.desk.order(a, b)
        with self.assertRaisesRegex(LookupError, 'unknown revision'):
            self.desk.order(999, a)
        self.assertEqual(self.seal_counts(), before)
        self.assertEqual(load_order(self.connection, existing).state, OrderState.PENDING)

    def test_invalid_vertex_records(self):
        invalid = (
            ('A', [(0, 0, 0)]),
            ('A', [(0, 0, 0), (0, 0, 2)]),
            ('A', [(0, 0, 0), (1.0, 0, 2)]),
            ('A', [(0, 0, 0), (1, 0, '1/0')]),
            ('A', [(0, 0, 0), (True, 0, 1)]),
            ('A', {(0, 0, 0), (1, 0, 1)}),
            (' ', RETURN_A),
        )
        for name, vertices in invalid:
            with self.subTest(name=name, vertices=vertices):
                with self.assertRaises(ValueError):
                    self.desk.register(name, vertices)
        self.assertEqual(self.revision_count(), 0)

    def revision_count(self):
        return self.connection.execute('SELECT COUNT(*) FROM survey_revisions').fetchone()[0]
