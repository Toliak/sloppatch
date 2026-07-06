import dataclasses
from typing import List, Optional

from .convert_data import Hunk, HunkLine
from ..utils.types import LineNmb


@dataclasses.dataclass(frozen=True, slots=True)
class PreparedAfterLine(HunkLine):
    original: Optional[str]
    """
    Line from the source text
    """
    no_newline: bool


@dataclasses.dataclass
class PreparedHunk(Hunk):
    begin_source_line: LineNmb
    synced_after_lines: List[PreparedAfterLine]


PreparedPatch = List[PreparedHunk]
"""
The Patch final stage.
"""
