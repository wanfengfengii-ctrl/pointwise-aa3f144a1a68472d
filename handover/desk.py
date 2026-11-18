import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from handover import bundles, history, receipts, session
from jobs import selection
from packages import publish as sealing
from packages.contacts import ContactPackage
from review import issue as signing
from review.store import WindowReport
from survey import intake


class HandoverDesk:
    def __init__(self, path: str | Path):
        self._connection = session.open_database(path)
        try:
            self.initialize()
        except BaseException:
            self.close()
            raise

    def __enter__(self) -> 'HandoverDesk':
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def close(self) -> None:
        self._connection.close()

    def initialize(self) -> None:
        session.initialize_database(self._connection)

    def register(self, line_code: str, vertices) -> int:
        with session.write_transaction(self._connection):
            result = intake.register(self._connection, line_code, vertices)
        return result

    def order(self, a_revision_id: int, b_revision_id: int) -> int:
        with session.write_transaction(self._connection):
            result = selection.order(self._connection, a_revision_id, b_revision_id)
        return result

    def publish(self, order_id: int) -> receipts.SealReceipt:
        with session.write_transaction(self._connection):
            result = sealing.publish(self._connection, order_id)
        return result

    def get_package(self, package_id: int) -> ContactPackage:
        return bundles.get_package(self._connection, package_id)

    def retire(self, revision_id: int) -> None:
        with session.write_transaction(self._connection):
            intake.retire(self._connection, revision_id)

    def issue(self, package_id: int, left, right) -> WindowReport:
        with session.write_transaction(self._connection):
            report = signing.issue(self._connection, package_id, left, right)
        return report

    def get_report(self, report_id: int) -> WindowReport:
        return history.get_report(self._connection, report_id)

    def get_receipt(self, receipt_id: int) -> receipts.SealReceipt:
        return receipts.load_receipt(self._connection, receipt_id)


def _report_rows(report: WindowReport) -> list:
    return [[contact.kind, list(map(str, contact.start)), list(map(str, contact.end))]
            for contact in report.contacts]


def _demo(root: Path) -> int:
    source = json.loads((root / 'samples' / 'return-survey.json').read_text(encoding='utf-8'))
    with TemporaryDirectory(prefix='survey-demo-') as directory:
        path = Path(directory) / 'patrol.sqlite3'
        with HandoverDesk(path) as desk:
            a = desk.register(source['a']['line_code'], source['a']['vertices'])
            b = desk.register(source['b']['line_code'], source['b']['vertices'])
            receipt = desk.publish(desk.order(a, b))
            desk.retire(a)
            desk.retire(b)
            package = desk.get_package(receipt.package_id)
            full = desk.issue(receipt.package_id, *source['full_window'])
            section = desk.issue(receipt.package_id, *source['section_window'])
            desk.register(source['a']['line_code'], source['correction'])
        with HandoverDesk(path) as desk:
            desk.initialize()
            archived_full = desk.get_report(full.report_id)
            archived_section = desk.get_report(section.report_id)
            if (archived_full != full or archived_section != section or
                    desk.get_receipt(receipt.receipt_id) != receipt or
                    desk.get_package(receipt.package_id) != package):
                raise AssertionError('archived handover disagrees with signed results')
        actual_evidence = [
            [row.a_segment, row.b_segment, list(map(str, row.start.stations)),
             list(map(str, row.end.stations))] for row in package.contacts
        ]
        downstream = {'full': _report_rows(archived_full), 'section': _report_rows(archived_section)}
        if actual_evidence != source['expected_evidence'] or downstream != source['expected_reports']:
            raise AssertionError(f'unexpected handover results: {actual_evidence!r}, {downstream!r}')
        marker = {
            'case_id': 'v2',
            'input': {key: source[key] for key in ('a', 'b', 'full_window', 'section_window')},
            'expected': source['expected_evidence'],
            'actual': actual_evidence,
            'downstream_expected': source['expected_reports'],
            'downstream_actual': downstream,
            'code_paths': ['packages/geometry.py', 'packages/contacts.py', 'review/continuity.py',
                           'review/clipping.py', 'handover/history.py'],
            'oracle': '按两条水平测线逐原段手算经过与端点，再按甲线里程截窗',
        }
        print('POINTWISE_SCENARIO ' + json.dumps(marker, ensure_ascii=False, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='管廊测线交班台')
    parser.add_argument('command', choices=('verify', 'demo'))
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    if args.command == 'demo':
        return _demo(root)
    suite = unittest.defaultTestLoader.discover(str(root / 'tests'), top_level_dir=str(root))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() and result.testsRun else 1


if __name__ == '__main__':
    raise SystemExit(main())
