from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from handover.desk import HandoverDesk


RETURN_A = [(0, 0, 0), (4, 0, 4), (0, 0, 8)]
SPLIT_B = [(3, 0, 0), (2, 0, 1), (1, 0, 2)]


def evidence_rows(package):
    return [(row.a_segment, row.b_segment, row.start.stations, row.end.stations)
            for row in package.contacts]


def report_rows(report):
    return [(row.kind, row.start, row.end) for row in report.contacts]


@contextmanager
def fail_at_commit(connection, operation):
    # These triggers run only after the last business write. The real engine
    # defers checking the deliberately missing parent until COMMIT.
    trigger_events = {
        'publish': 'AFTER UPDATE OF state ON main.orders',
        'issue': 'AFTER INSERT ON main.report_pickups',
    }
    event = trigger_events[operation]
    connection.execute('CREATE TEMP TABLE commit_parent (id INTEGER PRIMARY KEY)')
    connection.execute('''
        CREATE TEMP TABLE commit_guard (
            missing_parent INTEGER REFERENCES commit_parent(id) DEFERRABLE INITIALLY DEFERRED
        )
    ''')
    connection.execute(f'''
        CREATE TEMP TRIGGER reject_commit {event}
        BEGIN INSERT INTO commit_guard VALUES (1); END
    ''')
    try:
        yield
    finally:
        connection.execute('DROP TRIGGER temp.reject_commit')
        connection.execute('DROP TABLE temp.commit_guard')
        connection.execute('DROP TABLE temp.commit_parent')


class DeskCase(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory(prefix='survey-test-')
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / 'patrol.sqlite3'
        self._open()

    def _open(self):
        self.desk = HandoverDesk(self.path)
        self.addCleanup(self.desk.close)

    def reopen(self):
        self.desk.close()
        self._open()

    @property
    def connection(self):
        return self.desk._connection

    def make_order(self, a=RETURN_A, b=SPLIT_B):
        a_id = self.desk.register('A', a)
        b_id = self.desk.register('B', b)
        return a_id, b_id, self.desk.order(a_id, b_id)

    def seal(self, a=RETURN_A, b=SPLIT_B):
        a_id, b_id, order_id = self.make_order(a, b)
        return a_id, b_id, self.desk.publish(order_id)

    def stop_sources(self, *revision_ids):
        for revision_id in revision_ids:
            self.desk.retire(revision_id)

    def seal_counts(self):
        return self.connection.execute('''
            SELECT (SELECT COUNT(*) FROM orders),
                   (SELECT COUNT(*) FROM packages),
                   (SELECT COUNT(*) FROM seal_receipts)
        ''').fetchone()

    def issue_counts(self):
        return self.connection.execute('''
            SELECT (SELECT COUNT(*) FROM reports), (SELECT COUNT(*) FROM report_pickups)
        ''').fetchone()
