from dataclasses import dataclass
from fractions import Fraction

from packages.geometry import HitEndpoint, segment_intersection
from survey.revisions import SurveyRevision
from survey.segments import SurveySegment, original_segments


@dataclass(frozen=True, slots=True)
class ContactEndpoint:
    a_station: Fraction
    b_station: Fraction
    x: Fraction
    y: Fraction

    @property
    def stations(self) -> tuple[Fraction, Fraction]:
        return self.a_station, self.b_station

    @property
    def xy(self) -> tuple[Fraction, Fraction]:
        return self.x, self.y


@dataclass(frozen=True, slots=True)
class SegmentContact:
    a_segment: int
    b_segment: int
    start: ContactEndpoint
    end: ContactEndpoint

    @property
    def is_point(self) -> bool:
        return self.start.a_station == self.end.a_station


@dataclass(frozen=True, slots=True)
class ContactPackage:
    order_id: int
    a_revision_id: int
    b_revision_id: int
    a_bounds: tuple[Fraction, Fraction]
    b_bounds: tuple[Fraction, Fraction]
    a_segment_count: int
    b_segment_count: int
    contacts: tuple[SegmentContact, ...]


def _mileage_endpoint(a: SurveySegment, b: SurveySegment, hit: HitEndpoint) -> ContactEndpoint:
    alpha, beta, x, y = hit
    return ContactEndpoint(a.station_at(alpha), b.station_at(beta), x, y)


def build_segment_contacts(a: SurveyRevision, b: SurveyRevision) -> tuple[SegmentContact, ...]:
    """Keep one exact contact for each intersecting original segment pair."""
    a_segments = original_segments(a)
    b_segments = original_segments(b)
    contacts = []
    for a_segment in a_segments:
        for b_segment in b_segments:
            hit = segment_intersection(a_segment, b_segment)
            if hit is not None:
                contacts.append(SegmentContact(
                    a_segment.number,
                    b_segment.number,
                    _mileage_endpoint(a_segment, b_segment, hit.start),
                    _mileage_endpoint(a_segment, b_segment, hit.end),
                ))
    return tuple(contacts)
