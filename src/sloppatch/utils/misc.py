import re
from typing import List, Tuple

ANY_WHITESPACE_RE = re.compile(r"\s+")
STRING_ANY_EOL_RE = re.compile(r"^.+(\n|\r\n|\r)$")

def range_list_contains(idx: int, range_list: List[Tuple[int, int]]) -> bool:
    """
    range_list is the list of ranges: begin -- incl, end -- excl.
    """

    for r in range_list:
        if r[0] <= idx < r[1]:
            return True

    return False

def str_ends_with_eol(s: str) -> bool:
    if not s:
        return False

    last = s[-1]
    return last == '\n' or last == '\r'
