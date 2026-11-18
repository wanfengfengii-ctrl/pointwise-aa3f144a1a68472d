from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable

from packages.contacts import ContactEndpoint, SegmentContact


Seam = tuple[Fraction, Fraction, bool]


@dataclass(frozen=True, slots=True)
class OverlapRun:
    pieces: tuple[SegmentContact, ...]


def _seam(endpoint: ContactEndpoint, increasing_b: bool) -> Seam:
    return *endpoint.stations, increasing_b


def merge_overlaps(contacts: Iterable[SegmentContact]) -> tuple[OverlapRun, ...]:
    starts: dict[Seam, SegmentContact] = {}
    ends: dict[Seam, SegmentContact] = {}
    for contact in contacts:
        if contact.is_point:
            continue
        increasing_b = contact.end.b_station > contact.start.b_station
        start = _seam(contact.start, increasing_b)
        end = _seam(contact.end, increasing_b)
        if start in starts or end in ends:
            raise ValueError('ambiguous directed seam in contact evidence')
        starts[start] = contact
        ends[end] = contact

    # A station strictly increases on every piece, so all chains have a head.
    runs = []
    for start in sorted(starts.keys() - ends.keys()):
        pieces = []
        seam = start
        while seam in starts:
            piece = starts[seam]
            pieces.append(piece)
            seam = _seam(piece.end, start[2])
        runs.append(OverlapRun(tuple(pieces)))
    return tuple(runs)
