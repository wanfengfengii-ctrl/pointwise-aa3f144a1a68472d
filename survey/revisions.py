from dataclasses import dataclass
from enum import StrEnum
import json

from survey.vertices import Vertex, decode_ratio, parse_vertices


class RevisionStatus(StrEnum):
    AVAILABLE = 'available'
    RETIRED = 'retired'


@dataclass(frozen=True, slots=True)
class SurveyRevision:
    revision_id: int
    line_code: str
    ordinal: int
    status: RevisionStatus
    vertices: tuple[Vertex, ...]


def encode_revision_vertices(vertices: tuple[Vertex, ...]) -> str:
    rows = [[str(vertex.x), str(vertex.y), str(vertex.station)] for vertex in vertices]
    return json.dumps(rows, separators=(',', ':'))


def decode_revision_vertices(payload: str) -> tuple[Vertex, ...]:
    rows = json.loads(payload)
    if not isinstance(rows, list):
        raise ValueError('invalid stored vertices')
    for row in rows:
        if not isinstance(row, list) or len(row) != 3:
            raise ValueError('invalid stored vertex')
    return parse_vertices(tuple(decode_ratio(value) for value in row) for row in rows)
