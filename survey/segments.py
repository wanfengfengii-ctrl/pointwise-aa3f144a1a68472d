from dataclasses import dataclass
from fractions import Fraction

from survey.revisions import SurveyRevision
from survey.vertices import Vertex


@dataclass(frozen=True, slots=True)
class SurveySegment:
    number: int
    start: Vertex
    end: Vertex

    def station_at(self, parameter: Fraction) -> Fraction:
        return self.start.station + parameter * (self.end.station - self.start.station)


def original_segments(revision: SurveyRevision) -> tuple[SurveySegment, ...]:
    pairs = zip(revision.vertices, revision.vertices[1:])
    return tuple(SurveySegment(number, start, end) for number, (start, end) in enumerate(pairs, 1))
