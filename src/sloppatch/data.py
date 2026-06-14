import dataclasses
import enum
from typing import List


class RawAct(enum.Enum):
    Context = 'Context'
    Add = 'Add'
    Delete = 'Delete'

    def is_after(self):
        return self == RawAct.Context or self == RawAct.Add

    def is_before(self):
        return self == RawAct.Context or self == RawAct.Delete

@dataclasses.dataclass(frozen=True)
class RawChange:
    act: RawAct
    line: str

RawHunkChanges = List[RawChange]

@dataclasses.dataclass(frozen=True)
class RawHunkData:
    line: int
    """
    Line in the text to begin with
    """
    length: int
    

@dataclasses.dataclass
class RawHunk:
    before: RawHunkData
    after: RawHunkData
    comment: str
    changes: RawHunkChanges

    def str_header(self) -> str:
        return f"@@ -{self.before.line},{self.before.length} +{self.after.line},{self.after.length} @@"


RawPatch = List[RawHunk]

@dataclasses.dataclass
class HunkData:
    line: int
    """
    Line in the text to begin with
    """

    lines: List[str]

@dataclasses.dataclass
class Hunk:
    before: HunkData
    after: HunkData
    comment: str
    changes: RawHunkChanges
    """
    Raw changes info
    """

    def str_header(self) -> str:
        return (
            f"@@ -{self.before.line},{len(self.before.lines)} " +
            f"+{self.after.line},{len(self.after.lines)} @@"
        )


Patch = List[Hunk]