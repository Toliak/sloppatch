"""
Patch, Stage 2.

RawPatch text into the Patch (ready to apply over a file).
Without knowledge of the target file.
"""

import dataclasses
import re
from typing import List, Optional, Tuple, assert_never

from .util_mask import line_to_mask

from .convert_data import BeforeLine, Hunk, HunkLine, Patch
from ..utils.types import LineNmb

from .raw_parse_data import RawHunk, RawPatch
from ..utils.misc import ANY_WHITESPACE_RE

from ..error import SloppatchError
from ..config import (
    PatchConfig,
    ParseConfig,
)


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
    line_before_ranges: List[Tuple[LineNmb, LineNmb, Hunk]] = []

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
