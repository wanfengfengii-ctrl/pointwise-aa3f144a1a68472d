from dataclasses import dataclass
from fractions import Fraction

from survey.vertices import parse_rational


@dataclass(frozen=True, slots=True)
class MileageWindow:
    left: Fraction
    right: Fraction

    def contains(self, station: Fraction) -> bool:
        return self.left <= station <= self.right


def validate_window(left, right, a_bounds: tuple[Fraction, Fraction]) -> MileageWindow:
    left, right = parse_rational(left), parse_rational(right)
    if left > right:
        raise ValueError('window endpoints are inverted')
    if left < a_bounds[0] or right > a_bounds[1]:
        raise ValueError('window outside A station range')
    return MileageWindow(left, right)
