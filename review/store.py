from dataclasses import dataclass
import json
import sqlite3

from review.clipping import ReportContact, StationPair
from review.windows import MileageWindow
from survey.vertices import decode_ratio


@dataclass(frozen=True, slots=True)
class WindowReport:
    report_id: int
    package_id: int
    window: MileageWindow
    contacts: tuple[ReportContact, ...]


def ensure_report_schema(connection: sqlite3.Connection) -> None:
    connection.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            report_id INTEGER PRIMARY KEY,
            package_id INTEGER NOT NULL REFERENCES packages(package_id),
            left_station TEXT NOT NULL,
            right_station TEXT NOT NULL,
            contacts TEXT NOT NULL,
            UNIQUE (report_id, package_id)
        )
    ''')


def _encode_contacts(contacts: tuple[ReportContact, ...]) -> str:
    rows = [[contact.kind, [str(value) for value in contact.start],
             [str(value) for value in contact.end]] for contact in contacts]
    return json.dumps(rows, separators=(',', ':'))


def _decode_pair(value) -> StationPair:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError('invalid report station pair')
    return decode_ratio(value[0]), decode_ratio(value[1])


def _decode_contacts(payload: str, window: MileageWindow) -> tuple[ReportContact, ...]:
    rows = json.loads(payload)
    if not isinstance(rows, list):
        raise ValueError('invalid stored report contacts')
    contacts = []
    for row in rows:
        if not isinstance(row, list) or len(row) != 3:
            raise ValueError('invalid stored report contact')
        kind, start, end = row
        contact = ReportContact(_decode_pair(start), _decode_pair(end))
        a0, b0 = contact.start
        a1, b1 = contact.end
        if not window.left <= a0 <= a1 <= window.right or kind != contact.kind:
            raise ValueError('invalid stored report endpoints or kind')
        if kind != 'point' and (a0 == a1 or b0 == b1):
            raise ValueError('invalid stored report overlap')
        if contacts and contacts[-1] >= contact:
            raise ValueError('stored report contacts are not in strict order')
        contacts.append(contact)
    return tuple(contacts)


def insert_report(
    connection: sqlite3.Connection, package_id: int, window: MileageWindow,
    contacts: tuple[ReportContact, ...],
) -> WindowReport:
    cursor = connection.execute('''
        INSERT INTO reports (package_id, left_station, right_station, contacts) VALUES (?, ?, ?, ?)
    ''', (package_id, str(window.left), str(window.right), _encode_contacts(contacts)))
    return WindowReport(cursor.lastrowid, package_id, window, contacts)


def load_report(connection: sqlite3.Connection, report_id: int) -> WindowReport:
    if type(report_id) is not int or report_id <= 0:
        raise ValueError('report number must be a positive integer')
    row = connection.execute('''
        SELECT package_id, left_station, right_station, contacts FROM reports WHERE report_id = ?
    ''', (report_id,)).fetchone()
    if row is None:
        raise LookupError(f'unknown report {report_id}')
    package_id, left, right, payload = row
    try:
        window = MileageWindow(decode_ratio(left), decode_ratio(right))
        if window.left > window.right:
            raise ValueError('inverted stored window')
        contacts = _decode_contacts(payload, window)
    except (ValueError, TypeError) as error:
        raise ValueError(f'invalid report {report_id}: {error}') from error
    return WindowReport(report_id, package_id, window, contacts)
