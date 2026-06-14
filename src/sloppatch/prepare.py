from bisect import bisect_left, bisect_right
import dataclasses
import enum
from typing import Dict, Generator, Iterable, Iterator, List, Sequence, Tuple, Type

from .error import SloppatchError
from .whatthepatch_regexp import unified_hunk_start, unified_change
from .data import Patch, RawAct, RawHunk, RawHunkData, RawHunkChanges, RawChange, RawPatch, Hunk, HunkData

@dataclasses.dataclass(frozen=True)
class CountLinesResult:
    before: int
    after: int

def _count_hunk_lines(changes: RawHunkChanges) -> CountLinesResult:
    r_before = 0
    r_after = 0
    for c in changes:
        r_before += int(c.act.is_before())
        r_after += int(c.act.is_after())

    return CountLinesResult(r_before, r_after)


class RawHunkValidationError(SloppatchError):
    def __init__(self, raw_hunk: RawHunk, message: str):
        super().__init__(f"Raw Hunk validation error: '{message}'. Hunk: {raw_hunk.str_header()}")
        self.raw_hunk = raw_hunk


def raise_validate_raw_hunk(raw_hunk: RawHunk) -> None:
    expected_after_length = raw_hunk.after.length
    expected_before_length = raw_hunk.before.length

    before_line = raw_hunk.before.line
    after_line = raw_hunk.after.line
    if before_line < 1:
        raise RawHunkValidationError(
            raw_hunk,
            f"Line number (original) must start from 1. Got {before_line}"
        )
    if after_line < 1:
        raise RawHunkValidationError(
            raw_hunk,
            f"Line number (new) must start from 1. Got {after_line}"
        )

    lines = _count_hunk_lines(raw_hunk.changes)
    if expected_before_length != lines.before:
        raise RawHunkValidationError(
            raw_hunk,
            f"Original line count in hunk ({lines.before}) does not match header ({expected_before_length})"
        )

    if expected_after_length != lines.after:
        raise RawHunkValidationError(
            raw_hunk,
            f"New line count in hunk ({lines.after}) does not match header ({expected_after_length})"
        )
    
    if lines.after == 0 and lines.before == 0:
        raise RawHunkValidationError(
            raw_hunk,
            f"Empty hunk (no lines inside)"
        )


def validate_raw_hunk(raw_hunk: RawHunk) -> bool:
    try:
        raise_validate_raw_hunk(raw_hunk)
    except RawHunkValidationError as _e:
        return False
    else:
        return True

class RawPatchValidationError(SloppatchError):
    def __init__(self, raw_patch: RawPatch, raw_hunk: RawHunk, message: str):
        super().__init__(f"Raw Patch validation error: '{message}'. In hunk: {raw_hunk.str_header()}")
        self.raw_patch = raw_patch
        self.raw_hunk = raw_hunk


def raise_validate_raw_patch(raw_patch: RawPatch) -> None:
    line_before_ranges: List[Tuple[int, int]] = []
    line_after_ranges: List[Tuple[int, int]] = []

    # Verify each hunk
    for hunk in raw_patch:
        raise_validate_raw_hunk(hunk)

    # Verify the absence of range overlaps
    for hunk in raw_patch:
        lb_begin = hunk.before.line
        lb_end = hunk.before.line + hunk.before.length
        la_begin = hunk.after.line
        la_end = hunk.after.line + hunk.after.length

        for r in line_before_ranges:
            if r[0] < lb_end and r[1] > lb_begin:
                raise RawPatchValidationError(
                    raw_patch,
                    hunk,
                    "Hunk original lines overlap. " +
                    f"Existing range: ({r[0]},{r[1]}). New range: ({lb_begin}{lb_end})"
                )

        for r in line_after_ranges:
            if r[0] < la_end and r[1] > la_begin:
                raise RawPatchValidationError(
                    raw_patch,
                    hunk,
                    "Hunk new lines overlap. " +
                    f"Existing range: ({r[0]},{r[1]}). New range: ({la_begin}{la_end})"
                )

        line_before_ranges.append((lb_begin, lb_end))
        line_after_ranges.append((la_begin, la_end))

    # Verify "after" start line math
    deltas: Dict[int, int] = dict()
    for hunk in raw_patch:
        key = hunk.before.line
        delta = hunk.after.length - hunk.before.length
        if delta == 0:
            continue

        deltas[key] = delta

    keys: List[int] = list(sorted(deltas.keys()))

    for hunk in raw_patch:
        # Finds the index in range `[0, len(keys)]`
        # Bisect left, because we must not include the current line's key
        keys_to_check_idx = bisect_left(keys, hunk.before.line)
        keys_to_check = keys[:keys_to_check_idx]
        delta = sum(deltas[v] for v in keys_to_check)

        if hunk.before.line + delta != hunk.after.line:
            raise RawPatchValidationError(
                raw_patch,
                hunk,
                "Original start line and new start line validation failed. " +
                f"Hunk header: {hunk.str_header()}. "
                f"Delta: ({delta})"
            )


def raw_hunk_convert(raw_hunk: RawHunk) -> Hunk:
    """
    Converts hunk (without validation)
    """

    lines_before: List[str] = []
    lines_after: List[str] = []
    for c in raw_hunk.changes:
        if c.act.is_before():
            lines_before.append(c.line)
        if c.act.is_after():
            lines_after.append(c.line)

    return Hunk(
        before=HunkData(
            line=raw_hunk.before.line,
            lines=lines_before,
        ),
        after=HunkData(
            line=raw_hunk.after.line,
            lines=lines_after,
        ),
        comment=raw_hunk.comment,
        changes=raw_hunk.changes,
    )

def raw_patch_convert(raw: RawPatch) -> Patch:
    """
    Validates and converts the RawPatch into Patch
    """
    raise_validate_raw_patch(raw)
    return [
        raw_hunk_convert(hunk)
        for hunk in raw
    ]
