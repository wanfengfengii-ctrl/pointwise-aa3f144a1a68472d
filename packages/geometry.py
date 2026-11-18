from dataclasses import dataclass
from fractions import Fraction

from survey.segments import SurveySegment


Point = tuple[Fraction, Fraction]
# Endpoint entries contain the two local parameters followed by x and y.
HitEndpoint = tuple[Fraction, Fraction, Fraction, Fraction]


@dataclass(frozen=True, slots=True)
class SegmentHit:
    start: HitEndpoint
    end: HitEndpoint


def _difference(end: Point, start: Point) -> Point:
    return end[0] - start[0], end[1] - start[1]


def _cross(left: Point, right: Point) -> Fraction:
    return left[0] * right[1] - left[1] * right[0]


def _position(start: Point, delta: Point, parameter: Fraction) -> Point:
    return start[0] + parameter * delta[0], start[1] + parameter * delta[1]


def segment_intersection(a: SurveySegment, b: SurveySegment) -> SegmentHit | None:
    """Intersect two nondegenerate closed segments in A parameter order."""
    p, q = a.start.xy, b.start.xy
    r, s = _difference(a.end.xy, p), _difference(b.end.xy, q)
    offset = _difference(q, p)
    denominator = _cross(r, s)
    if denominator:
        alpha = _cross(offset, s) / denominator
        beta = _cross(offset, r) / denominator
        if 0 <= alpha <= 1 and 0 <= beta <= 1:
            endpoint = (alpha, beta, *_position(p, r, alpha))
            return SegmentHit(endpoint, endpoint)
        return None
    if _cross(offset, r):
        return None

    # Along a nonconstant coordinate, projection preserves collinear interval order.
    axis = 0 if r[0] else 1
    b_start = offset[axis] / r[axis]
    b_end = (b.end.xy[axis] - p[axis]) / r[axis]
    left = max(Fraction(0), min(b_start, b_end))
    right = min(Fraction(1), max(b_start, b_end))
    if left > right:
        return None

    def endpoint(alpha: Fraction) -> HitEndpoint:
        position = _position(p, r, alpha)
        beta = (position[axis] - q[axis]) / s[axis]
        return alpha, beta, *position

    return SegmentHit(endpoint(left), endpoint(right))
