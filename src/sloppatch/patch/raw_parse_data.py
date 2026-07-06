import dataclasses
import enum
from typing import List

from ..utils.types import LineNmb


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
