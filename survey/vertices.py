from collections.abc import Mapping, Set
from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True, slots=True)
class Vertex:
    x: Fraction
    y: Fraction
    station: Fraction

    @property
    def xy(self) -> tuple[Fraction, Fraction]:
        return self.x, self.y


def parse_rational(value: int | str | Fraction) -> Fraction:
    """Read an exact value from the public input types."""
    if isinstance(value, bool) or not isinstance(value, (int, str, Fraction)):
        raise ValueError('expected an integer, Fraction or rational string')
    try:
        return Fraction(value)
    except (ValueError, ZeroDivisionError) as error:
        raise ValueError('invalid rational value') from error


def decode_ratio(value: str) -> Fraction:
    if not isinstance(value, str):
        raise ValueError('stored rational must be a string')
    result = parse_rational(value)
    if value != str(result):
        raise ValueError('stored rational must be canonical')
    return result


def _parse_vertex(record) -> Vertex:
    if isinstance(record, Vertex):
        record = (*record.xy, record.station)
    if isinstance(record, (str, bytes, bytearray, Mapping, Set)):
        raise ValueError('expected an ordered vertex triple')
    try:
        x, y, station = record
    except (TypeError, ValueError) as error:
        raise ValueError('expected a vertex with x, y and station') from error
    return Vertex(parse_rational(x), parse_rational(y), parse_rational(station))


def parse_vertices(records) -> tuple[Vertex, ...]:
    if isinstance(records, (str, bytes, bytearray, Mapping, Set)):
        raise ValueError('expected an ordered sequence of vertices')
    try:
        source = iter(records)
    except TypeError as error:
        raise ValueError('expected an ordered sequence of vertices') from error
    vertices = tuple(_parse_vertex(record) for record in source)
    if len(vertices) < 2:
        raise ValueError('a survey needs at least two vertices')
    for previous, current in zip(vertices, vertices[1:]):
        if current.xy == previous.xy:
            raise ValueError('adjacent coordinates must differ')
        if current.station <= previous.station:
            raise ValueError('station must strictly increase')
    return vertices
