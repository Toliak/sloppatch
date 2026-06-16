import dataclasses
from typing import Iterable, List, Optional

from .error import SloppatchError
from .whatthepatch_regexp import unified_hunk_start, unified_change
from .data import RawAct, RawHunk, RawHunkData, RawChange, RawPatch, ParseConfig


def char_to_act(c: str) -> RawAct:
    if c == "+":
        return RawAct.Add
    if c == "-":
        return RawAct.Delete

    return RawAct.Context


class LineParseError(SloppatchError):
    pass

def lines_to_raw_changes(
    lines_itr: Iterable[str], cfg: Optional[ParseConfig] = None
) -> RawPatch:
    """
    Accept lines with '\n'
    """
    cfg_ready = cfg if cfg is not None else ParseConfig()

    result: List[RawHunk] = []
    for i, line in enumerate(lines_itr):
        line_idx = i + 1
        if not line:
            if cfg_ready.skip_raw_empty_lines:
                continue
            raise LineParseError(f"Empty line {line_idx}")

        start_m = unified_hunk_start.match(line)
        if start_m:
            hunk = RawHunk(
                before=RawHunkData(
                    line=int(start_m.group(1)),
                    length=int(start_m.group(2)),
                ),
                after=RawHunkData(
                    line=int(start_m.group(3)),
                    length=int(start_m.group(4)),
                ),
                comment=start_m.group(5),
                changes=[],
            )
            result.append(hunk)
            continue

        change_m = unified_change.match(line)
        if change_m:
            if not result:
                if cfg_ready.skip_raw_orphaned_changes:
                    continue
                raise LineParseError(
                    f"Change without hunk on line {line_idx}. "
                    f"Line beginning: '{line[:16]}'..."
                )
            current_hunk = result[-1]
            change = RawChange(
                act=char_to_act(change_m.group(1)), line=change_m.group(2)
            )
            current_hunk.changes.append(change)
            continue

        if cfg_ready.skip_raw_wrong_format_lines:
            continue
        raise LineParseError(
            f"Line {line_idx} with wrong format. Line beginning: '{line[:16]}'..."
        )

    return result
