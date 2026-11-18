from fractions import Fraction
import unittest

from packages.geometry import SegmentHit, segment_intersection
from survey.segments import SurveySegment
from survey.vertices import parse_vertices


def segment(start, end):
    return SurveySegment(1, *parse_vertices([(*start, 0), (*end, 1)]))


class GeometryTests(unittest.TestCase):
    def test_vertical_overlap_with_reverse_parameters(self):
        a = segment((1, 0), (1, 3))
        b = segment((1, 4), (1, 1))
        self.assertEqual(segment_intersection(a, b), SegmentHit(
            (Fraction(1, 3), 1, 1, 1), (1, Fraction(1, 3), 1, 3),
        ))

    def test_collinear_endpoint_only(self):
        a = segment((0, 0), (1, 1))
        b = segment((2, 2), (1, 1))
        self.assertEqual(segment_intersection(a, b), SegmentHit((1, 1, 1, 1), (1, 1, 1, 1)))

    def test_lines_intersect_outside_one_closed_segment(self):
        a = segment((0, 0), (1, 0))
        b = segment((2, -1), (2, 1))
        self.assertIsNone(segment_intersection(a, b))

    def test_parallel_and_collinear_disjoint_segments(self):
        a = segment((0, 0), (1, 0))
        self.assertIsNone(segment_intersection(a, segment((0, 1), (1, 1))))
        self.assertIsNone(segment_intersection(a, segment((2, 0), (3, 0))))
