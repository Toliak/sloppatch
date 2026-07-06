import dataclasses
from typing import List

from .raw_parse_data import RawAct, RawHunk


@dataclasses.dataclass(frozen=True, slots=True)
class HunkLine:
    line: str
    """
    Line from hunk
    """

    act: RawAct


@dataclasses.dataclass(frozen=True, slots=True)
class BeforeLine(HunkLine):
    mask: str
    """
    Line masked
    """


@dataclasses.dataclass
class Hunk(RawHunk):
    before_lines: List[BeforeLine]
    after_lines: List[HunkLine]


Patch = List[Hunk]
