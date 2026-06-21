import dataclasses
import enum
from typing import List, Literal, Optional

LineIdx = int
LineNmb = int

class RawAct(enum.Enum):
    Context = "Context"
    Add = "Add"
    Delete = "Delete"

    def is_after(self):
        return self == RawAct.Context or self == RawAct.Add

    def is_before(self):
        return self == RawAct.Context or self == RawAct.Delete


@dataclasses.dataclass(frozen=True, slots=True)
class RawChange:
    act: RawAct
    line: str
    no_newline: bool = False

RawHunkChanges = List[RawChange]


@dataclasses.dataclass
class RawHunk:
    start_line: LineNmb
    comment: str
    changes: RawHunkChanges
    """
    Raw changes info
    """

    def str_header(self) -> str:
        return f"# {self.start_line} # {self.comment}"


RawPatch = List[RawHunk]

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

@dataclasses.dataclass(frozen=True, slots=True)
class AfterLine(HunkLine):
    original: Optional[str]
    """
    Line from the source text
    """
    no_newline: bool

@dataclasses.dataclass
class PreparedHunk(Hunk):
    begin_source_line: LineNmb
    synced_after_lines: List[AfterLine]

PreparedPatch = List[PreparedHunk]
"""
The Patch final stage.
"""


@dataclasses.dataclass
class ParseConfig:
    raw_empty_lines_rule: Literal['strict', 'skip', 'as-empty-context-line'] = 'strict'
    """
    How to consider raw empty line in a hunk
    """

    raw_wrong_format_lines_rule: Literal['strict', 'skip'] = 'strict'
    """
    How to consider a line that starts with unknown character. Or has unknown format
    """

    raw_line_ltrim_rule: Literal['no', 'yes'] = 'no'
    """
    Trims the left side of the raw line.
    """

    raw_orphan_line_rule: Literal['strict', 'skip'] = 'strict'
    """
    What to do, if there are lines before the hunk beginning
    """

    raw_orphan_nonewline_rule: Literal['strict', 'skip'] = 'strict'
    """
    What to do, if there is NoNewLine line in empty hunk
    """

    raw_empty_hunk_rule: Literal['strict', 'skip'] = 'strict'
    """
    What to do with empty hunk
    """

@dataclasses.dataclass
class PatchConfig:
    fuzz_context_lines: int = 0
    """
    How many lines before/after can we search to get the real patch location
    """

    trim_string: bool = False
    """
    Trim the string while matching
    """

    ignore_whitespaces: bool = False
    """
    Completely ignore whitespaces while matching.
    When enabled, `trim_string` is automatically set to True.
    """

    ignore_case_rule: Literal['strict', 'ignore-all'] = 'strict'
    """
    strict -- do not ignore case.
    ignore-all -- Ignore case while matching any line.
    # ignore-context -- Ignore case while matching context lines.
    """