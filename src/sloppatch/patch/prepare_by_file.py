"""
Patch, Stage 3.

Patch into the PreparedPatch (with the file knowledge).
Applying to the file.
"""

import dataclasses
from typing import Iterable, Iterator, List, Optional, Tuple, assert_never

from sloppatch.patch.util_mask import line_to_mask

from .prepare_by_file_data import PreparedAfterLine, PreparedHunk, PreparedPatch

from .convert_data import BeforeLine, HunkLine, Patch, Hunk

from .raw_parse_data import RawAct, RawChange, RawHunk, RawHunkChanges
from ..utils.misc import range_list_contains
from ..utils.types import LineNmb

from ..config import (
    PatchConfig,
)
from ..error import SloppatchError
from ..utils.sparse_file import SparsePatchFile
from ..utils.spiral_range import spiral_range

def hunk_begin_line_range(
    hunk: RawHunk, file: SparsePatchFile, cfg: PatchConfig
) -> Tuple[LineNmb, LineNmb]:
    """
    Begin Inclusively
    End non-inclusively
    """
    file_lines_end = file.get_lines_end()
    return (
        max(hunk.start_line - cfg.fuzz_context_lines, 1),
        min(hunk.start_line + cfg.fuzz_context_lines + 1, file_lines_end),
    )


def prepare_file_cache(
    patch: Patch, cfg: PatchConfig, lines_itr: Iterable[str]
) -> SparsePatchFile:
    """
    Prepares data for patch

    lines_itr must contain list with EOL ('\n') at the end
    """

    if len(patch) == 0:
        return SparsePatchFile()

    fuzz_line_ranges: List[Tuple[LineNmb, LineNmb]] = []
    for hunk in patch:
        start_line = max(hunk.start_line - cfg.fuzz_context_lines, 1)
        end_line = (
            hunk.start_line
            + len(hunk.before_lines)
            + cfg.fuzz_context_lines
            + cfg.skip_context_lines
        )
        fuzz_line_ranges.append((start_line, end_line))

    first_line = min(v[0] for v in fuzz_line_ranges)
    last_line = max(v[1] for v in fuzz_line_ranges)

    file_cache = SparsePatchFile()
    # Here we cache the lines by their "masks" with regards to the `cfg``
    for line_idx, line in enumerate(lines_itr):
        line_nmb = line_idx + 1  # Patch numerates lines from 1
        if line_nmb < first_line:
            continue
        if line_nmb >= last_line:
            break

        if range_list_contains(line_nmb, fuzz_line_ranges):
            mask = line_to_mask(line, cfg)
            file_cache.add_new_line(line_nmb, line, mask)

    return file_cache


class ValidatePatchLinesError(SloppatchError):
    pass

@dataclasses.dataclass(frozen=True, slots=True)
class HunkPlaceAtLineSimilarity:
    max_change_idx: int

def hunk_place_at_line(
    hunk: Hunk, file: SparsePatchFile, line_nmb: LineNmb, cfg: PatchConfig
) -> Hunk | HunkPlaceAtLineSimilarity:
    """
    Returns a new hunk with the correct context.
    Or None if we are unable to place it.

    Can skip context and before-delete lines
    """
    new_raw_changes: RawHunkChanges = []
    new_before_lines: List[BeforeLine] = []
    new_after_lines: List[HunkLine] = []

    skip_context_offset = 0

    before_lines_i = 0
    after_lines_i = 0

    for change_idx, raw_change in enumerate(hunk.changes):
        match raw_change.act:
            case RawAct.Add:
                new_raw_changes.append(raw_change)
                new_after_lines.append(hunk.after_lines[after_lines_i])
                after_lines_i += 1

            case RawAct.Delete | RawAct.Context as in_act:
                hunk_line = hunk.before_lines[before_lines_i]
                line_in_file: LineNmb = line_nmb + before_lines_i + skip_context_offset

                line_found: bool = False
                skipped_lines: List[Tuple[str, str]] = []

                for skip_i in range(
                    0, (cfg.skip_context_lines - skip_context_offset) + 1
                ):
                    d = file.get_line_mask(line_in_file + skip_i)
                    if d is None:
                        # End of file or file cached fragment
                        return HunkPlaceAtLineSimilarity(change_idx)

                    _file_line_raw, file_line_mask = d
                    if file_line_mask != hunk_line.mask:
                        skipped_lines.append(d)
                    else:
                        line_found = True
                        break

                if line_found is False:
                    return HunkPlaceAtLineSimilarity(change_idx)

                for d in skipped_lines:
                    # "Edit" the patch, add skipped lines
                    new_raw_changes.append(RawChange(RawAct.Context, d[0]))
                    new_before_lines.append(BeforeLine(d[0], RawAct.Context, d[1]))
                    new_after_lines.append(
                        HunkLine(
                            d[0],
                            RawAct.Context,
                        )
                    )

                new_raw_changes.append(raw_change)
                new_before_lines.append(hunk_line)
                skip_context_offset += len(skipped_lines)
                before_lines_i += 1

                if in_act == RawAct.Context:
                    # For the Context: AfterLines must contain the current line
                    new_after_lines.append(hunk_line)
                    after_lines_i += 1

            case _:
                assert_never(raw_change.act)

    return Hunk(
        start_line=hunk.start_line,
        comment=hunk.comment,
        changes=new_raw_changes,
        before_lines=new_before_lines,
        after_lines=new_after_lines,
    )

@dataclasses.dataclass(frozen=True, slots=True)
class FuzzyMaxSimilarPlace:
    max_change_idx: int
    line: LineNmb

class ValidatePatchLinesSimilarityError(ValidatePatchLinesError):
    def __init__(self, similar: FuzzyMaxSimilarPlace, hunk: Hunk, *args):
        self.similar = similar
        self.hunk = hunk
        super().__init__(*args)


def hunk_fuzzy_place_line_nmb(
    hunk: Hunk, file: SparsePatchFile, cfg: PatchConfig
) -> Tuple[LineNmb, Hunk]:
    """
    The core function, that detects the Hunk's line number.

    Returns line number of the Hunk beginning
    """
    if not hunk.before_lines:
        return hunk.start_line, hunk

    range_begin, range_end = hunk_begin_line_range(hunk, file, cfg)

    max_similar: Optional[FuzzyMaxSimilarPlace] = None

    line_nmb: LineNmb
    for line_nmb in spiral_range(hunk.start_line, range_begin, range_end):
        r = hunk_place_at_line(hunk, file, line_nmb, cfg)
        match r:
            case Hunk() as h:
                return line_nmb, h
            case HunkPlaceAtLineSimilarity() as similarity:
                if max_similar is None or max_similar.max_change_idx < similarity.max_change_idx:
                    max_similar = FuzzyMaxSimilarPlace(
                        max_change_idx=similarity.max_change_idx,
                        line=line_nmb
                    )

    if max_similar is None:
        raise ValidatePatchLinesError(
                "Unable to find hunk application line. Got empty line range. Empty file? "
                + f"Hunk: {hunk.str_header()}. "
                + f"Line range: ({range_begin}, {range_end})"
            )
    else:
        raise ValidatePatchLinesSimilarityError(
            max_similar,
            hunk,
            "Unable to find hunk application line. "
            + f"Hunk: {hunk.str_header()}. "
            + f"Line range: ({range_begin}, {range_end})"
        )


def hunk_new_after_lines(
    hunk: Hunk, original_before_lines: List[str]
) -> List[PreparedAfterLine]:
    new_lines: List[PreparedAfterLine] = []
    original_line_idx = 0
    for c in hunk.changes:
        act = c.act
        match act:
            case RawAct.Delete:
                original_line_idx += 1
            case RawAct.Add:
                new_lines.append(
                    PreparedAfterLine(
                        line=c.line,
                        act=act,
                        original=None,
                        no_newline=c.no_newline if c.no_newline is not None else False,
                    )
                )
            case RawAct.Context:
                new_lines.append(
                    PreparedAfterLine(
                        line=c.line,
                        act=act,
                        original=original_before_lines[original_line_idx],
                        no_newline=False,
                    )
                )
                original_line_idx += 1
            case _:
                assert_never(act)

    assert len(new_lines) == len(hunk.after_lines)
    return new_lines


def prepare_patch_final(
    patch: Patch, file_cache: SparsePatchFile, cfg: PatchConfig
) -> PreparedPatch:
    """
    Validates patch. If something happens -- throws an error.
    Returns list of lines of beginnings of hunks. The same length as List[Hunk]
    """

    apply_line_idxs: List[LineNmb] = []
    patch_placed: Patch = []

    for i, hunk in enumerate(patch):
        line_nmb, new_hunk = hunk_fuzzy_place_line_nmb(hunk, file_cache, cfg)
        apply_line_idxs.append(line_nmb)
        patch_placed.append(new_hunk)

    assert len(apply_line_idxs) == len(patch) == len(patch_placed)

    # Validation: there must be no overlaps
    for i, (line_nmb, hunk) in enumerate(zip(apply_line_idxs, patch_placed)):
        range_begin = line_nmb  # incl
        range_end = line_nmb + len(hunk.before_lines)  # excl
        if range_begin == range_end:
            # Hunk with Add only edge-case
            range_end += 1

        for j in range(i + 1, len(patch_placed)):
            inner_i = apply_line_idxs[j]
            inner_hunk = patch_placed[j]

            inner_begin = inner_i
            inner_end = inner_i + len(inner_hunk.before_lines)
            if inner_begin == inner_end:
                # Hunk with Add only edge-case
                inner_end += 1

            if range_begin < inner_end and range_end > inner_begin:
                raise ValidatePatchLinesError(
                    "Hunks placement overlap. "
                    + f"Hunk1: {hunk.str_header()}, placement range: ({range_begin},{range_end}). "
                    + f"Hunk2: {inner_hunk.str_header()}, placement range: ({inner_begin},{inner_end})."
                )

    # Match after_line -> original line
    new_patch: List[PreparedHunk] = []
    for line_nmb, hunk in zip(apply_line_idxs, patch_placed):
        original_lines = [
            v[0]
            for v in [
                file_cache.get_line_mask(line_idx)
                for line_idx in range(line_nmb, line_nmb + len(hunk.before_lines))
            ]
            if v is not None
        ]
        assert len(original_lines) == len(hunk.before_lines)

        new_hunk = PreparedHunk(
            **hunk.__dict__,
            begin_source_line=line_nmb,
            synced_after_lines=hunk_new_after_lines(hunk, original_lines),
        )
        new_patch.append(new_hunk)

    return new_patch
