"""
RawHunks text into the Patch (ready to apply over a file).
Without knowledge of the target file.
"""

import dataclasses
import re
from typing import List, Optional, Tuple, assert_never

from .error import SloppatchError
from .data import (
    BeforeLine,
    HunkLine,
    Patch,
    PatchConfig,
    RawHunk,
    RawPatch,
    Hunk,
    ParseConfig,
)


@dataclasses.dataclass(frozen=True)
class CountLinesResult:
    before: int
    after: int


class RawHunkValidationError(SloppatchError):
    pass


def raise_validate_raw_hunk(raw_hunk: RawHunk, cfg: ParseConfig) -> Optional[RawHunk]:
    """
    RawHunk -- ok
    None -- skip the hunk

    Raised exception -- error
    """

    before_line = raw_hunk.start_line
    if before_line < 1:
        raise RawHunkValidationError(
            f"Line number (start) must start from 1. Got {before_line}"
        )

    if not raw_hunk.changes:
        match cfg.raw_empty_hunk_rule:
            case "skip":
                return None
            case "strict":
                raise RawHunkValidationError("Empty hunk (no lines inside)")

    if not any(change.act.is_before() for change in raw_hunk.changes):
        match cfg.hunk_add_only_rule:
            case "apply":
                pass
            case "reject":
                raise RawHunkValidationError(
                    "Hunks that contain only Add operations are prohibited"
                )

    return raw_hunk


class PatchValidationError(SloppatchError):
    pass


def raise_validate_patch(patch: Patch) -> None:
    line_before_ranges: List[Tuple[int, int, Hunk]] = []

    # Verify the absence of range overlaps
    for hunk in patch:
        lb_begin = hunk.start_line
        lb_end = lb_begin + len(hunk.before_lines)

        for r in line_before_ranges:
            in_begin, in_end, in_hunk = r
            if in_begin < lb_end and in_end > lb_begin:
                raise PatchValidationError(
                    "Hunks overlap. "
                    + f"Range 1: ({in_begin},{in_end}) from hunk '{in_hunk.str_header}'. "
                    + f"Range 2: ({lb_begin}{lb_end}) from hunk '{hunk.str_header}'. "
                    + "Consider to join two hunks into a single one.",
                )

        line_before_ranges.append((lb_begin, lb_end, hunk))


ANY_WHITESPACE_RE = re.compile(r"\s+")


def line_to_mask(line: str, cfg: PatchConfig) -> str:
    if not line:
        return line

    new_line = line
    if new_line[-1] == "\n":
        new_line = new_line[:-1]

    if cfg.ignore_whitespaces:
        new_line = re.sub(ANY_WHITESPACE_RE, "", new_line)

    if cfg.trim_string and not cfg.ignore_whitespaces:
        new_line = new_line.strip()

    match cfg.ignore_case_rule:
        case "strict":
            pass  # do noting
        case "ignore-all":
            new_line = new_line.lower()
        # case 'ignore-context':
        #     if act == RawAct.Context:
        #         new_line = new_line.lower()
        case _:
            assert_never(cfg.ignore_case_rule)

    return new_line


def raw_hunk_convert(raw_hunk: RawHunk, cfg: PatchConfig) -> Hunk:
    """
    Converts hunk (without validation)
    """

    before_lines: List[BeforeLine] = []
    after_lines: List[HunkLine] = []
    for c in raw_hunk.changes:
        if c.act.is_before():
            before_lines.append(
                BeforeLine(line=c.line, act=c.act, mask=line_to_mask(c.line, cfg))
            )
        if c.act.is_after():
            after_lines.append(
                HunkLine(
                    line=c.line,
                    act=c.act,
                )
            )

    return Hunk(
        **raw_hunk.__dict__,
        before_lines=before_lines,
        after_lines=after_lines,
    )


def raw_patch_convert(
    raw: RawPatch, parse_config: ParseConfig, patch_config: PatchConfig
) -> Patch:
    """
    Validates and converts the RawPatch into Patch
    """

    raw_filtered: RawPatch = []
    for i, hunk in enumerate(raw):
        try:
            v = raise_validate_raw_hunk(hunk, parse_config)
        except SloppatchError as e:
            raise RawHunkValidationError(
                f"Hunk number {i + 1}, header '{hunk.str_header()}'. " + str(e)
            ) from e

        if v is not None:
            raw_filtered.append(hunk)

    patch: Patch = [raw_hunk_convert(hunk, patch_config) for hunk in raw_filtered]
    raise_validate_patch(patch)
    return patch
