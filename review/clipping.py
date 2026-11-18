from dataclasses import dataclass
from fractions import Fraction

from packages.contacts import SegmentContact
from review.continuity import OverlapRun
from review.windows import MileageWindow


StationPair = tuple[Fraction, Fraction]


@dataclass(frozen=True, order=True, slots=True)
class ReportContact:
    start: StationPair
    end: StationPair

    @property
    def kind(self) -> str:
        if self.start == self.end:
            return 'point'
        return 'same' if self.end[1] > self.start[1] else 'reverse'


def _b_station(run: OverlapRun, a_station: Fraction) -> Fraction | None:
    for piece in run.pieces:
        start, end = piece.start, piece.end
        if start.a_station <= a_station <= end.a_station:
            proportion = (a_station - start.a_station) / (end.a_station - start.a_station)
            return start.b_station + proportion * (end.b_station - start.b_station)
    return None


def clip_run(run: OverlapRun, window: MileageWindow) -> ReportContact | None:
    left = max(window.left, run.pieces[0].start.a_station)
    right = min(window.right, run.pieces[-1].end.a_station)
    if left > right:
        return None
    b_left, b_right = _b_station(run, left), _b_station(run, right)
    if b_left is None or b_right is None:
        raise ValueError('gap inside an overlap run')
    return ReportContact((left, b_left), (right, b_right))


def settle_contacts(
    evidence: tuple[SegmentContact, ...], runs: tuple[OverlapRun, ...], window: MileageWindow
) -> tuple[ReportContact, ...]:
    results = set()
    for run in runs:
        clipped = clip_run(run, window)
        if clipped is not None:
            results.add(clipped)

    point_pairs = {
        contact.start.stations for contact in evidence
        if contact.is_point and window.contains(contact.start.a_station)
    }
    for a_station, b_station in point_pairs:
        if not any(_b_station(run, a_station) == b_station for run in runs):
            point = (a_station, b_station)
            results.add(ReportContact(point, point))
    return tuple(sorted(results))
