from fractions import Fraction
import json

from packages.contacts import ContactEndpoint, ContactPackage, SegmentContact
from survey.vertices import decode_ratio


_FIELDS = {
    'version', 'order_id', 'a_revision_id', 'b_revision_id', 'a_bounds', 'b_bounds',
    'a_segment_count', 'b_segment_count', 'contacts',
}


def _positive_integer(value) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError('expected a positive integer in package')
    return value


def _array(value, size: int) -> list:
    if not isinstance(value, list) or len(value) != size:
        raise ValueError(f'expected a package array of length {size}')
    return value


def _ratios(value, size: int) -> tuple[Fraction, ...]:
    return tuple(decode_ratio(item) for item in _array(value, size))


def _read_contact(row) -> SegmentContact:
    a_segment, b_segment, start, end = _array(row, 4)
    return SegmentContact(
        _positive_integer(a_segment), _positive_integer(b_segment),
        ContactEndpoint(*_ratios(start, 4)), ContactEndpoint(*_ratios(end, 4)),
    )


def _write_ratios(values) -> list[str]:
    if any(isinstance(value, bool) or not isinstance(value, (int, Fraction)) for value in values):
        raise ValueError('package requires exact rational values')
    return [str(value) for value in values]


def _write_contact(contact: SegmentContact) -> list:
    return [
        contact.a_segment, contact.b_segment,
        _write_ratios((*contact.start.stations, *contact.start.xy)),
        _write_ratios((*contact.end.stations, *contact.end.xy)),
    ]


def _validate_contacts(package: ContactPackage) -> None:
    previous = (0, 0)
    a_positions, b_positions = {}, {}
    for contact in package.contacts:
        pair = (_positive_integer(contact.a_segment), _positive_integer(contact.b_segment))
        if pair <= previous:
            raise ValueError('contact segment pairs must be unique and ordered')
        if pair[0] > package.a_segment_count or pair[1] > package.b_segment_count:
            raise ValueError('contact segment number outside package')
        previous = pair
        start, end = contact.start, contact.end
        if contact.is_point:
            if start != end:
                raise ValueError('point contact must have identical endpoints')
        elif end.a_station < start.a_station or end.b_station == start.b_station or start.xy == end.xy:
            raise ValueError('invalid overlap endpoints')
        for endpoint in (start, end):
            a_station, b_station = endpoint.stations
            if not package.a_bounds[0] <= a_station <= package.a_bounds[1]:
                raise ValueError('contact outside A station range')
            if not package.b_bounds[0] <= b_station <= package.b_bounds[1]:
                raise ValueError('contact outside B station range')
            if (a_positions.setdefault(a_station, endpoint.xy) != endpoint.xy or
                    b_positions.setdefault(b_station, endpoint.xy) != endpoint.xy):
                raise ValueError('contradictory positions at a fixed station')


def _validate_package(package: ContactPackage) -> None:
    for identity in (package.order_id, package.a_revision_id, package.b_revision_id,
                     package.a_segment_count, package.b_segment_count):
        _positive_integer(identity)
    for bounds in (package.a_bounds, package.b_bounds):
        if len(bounds) != 2 or bounds[0] >= bounds[1]:
            raise ValueError('invalid station range')
    _validate_contacts(package)


def encode_package(package: ContactPackage) -> str:
    _validate_package(package)
    payload = {
        'version': 1,
        'order_id': package.order_id,
        'a_revision_id': package.a_revision_id,
        'b_revision_id': package.b_revision_id,
        'a_bounds': _write_ratios(package.a_bounds),
        'b_bounds': _write_ratios(package.b_bounds),
        'a_segment_count': package.a_segment_count,
        'b_segment_count': package.b_segment_count,
        'contacts': [_write_contact(contact) for contact in package.contacts],
    }
    return json.dumps(payload, separators=(',', ':'), sort_keys=True)


def decode_package(payload: str) -> ContactPackage:
    raw = json.loads(payload)
    if not isinstance(raw, dict) or set(raw) != _FIELDS:
        raise ValueError('invalid package fields')
    if type(raw['version']) is not int or raw['version'] != 1:
        raise ValueError('unsupported package version')
    if not isinstance(raw['contacts'], list):
        raise ValueError('invalid contact list')
    package = ContactPackage(
        order_id=raw['order_id'],
        a_revision_id=raw['a_revision_id'],
        b_revision_id=raw['b_revision_id'],
        a_bounds=_ratios(raw['a_bounds'], 2),
        b_bounds=_ratios(raw['b_bounds'], 2),
        a_segment_count=raw['a_segment_count'],
        b_segment_count=raw['b_segment_count'],
        contacts=tuple(_read_contact(row) for row in raw['contacts']),
    )
    _validate_package(package)
    return package
