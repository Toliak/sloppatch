"""
Patch into the PreparedPatch (with the file knowledge).
Applying to the file.
"""

from typing import Iterable, Iterator, List, Tuple, assert_never

from .data import (
    AfterLine,
    LineNmb,
    PatchConfig,
    PreparedHunk,
    PreparedPatch,
    RawAct,
    RawChange,
    RawHunk,
)
from .error import SloppatchError, SloppatchInternalError
from .sparse_file import SparsePatchFile
from .prepare import Patch, Hunk, line_to_mask


def _is_idx_in_range(idx: int, range_list: List[Tuple[int, int]]) -> bool:
    for r in range_list:
        if r[0] <= idx < r[1]:
            return True

    return False


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
        end_line = hunk.start_line + len(hunk.before_lines) + cfg.fuzz_context_lines
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

        if _is_idx_in_range(line_nmb, fuzz_line_ranges):
            mask = line_to_mask(line, cfg)
            file_cache.add_new_line(line_nmb, line, mask)

    return file_cache


def spiral_range(start: int, range_begin: int, range_end: int) -> Iterator[int]:
    if not (range_begin <= start < range_end):
        return

    yield start

    begin_delta = abs(start - range_begin) + 1  # Included the begin nmb
    end_delta = abs(range_end - start)
    for delta in range(1, max(begin_delta, end_delta)):
        start_minus_delta = start - delta
        if range_begin <= start_minus_delta < range_end:
            yield start_minus_delta

        start_plus_delta = start + delta
        if range_begin <= start_plus_delta < range_end:
            yield start_plus_delta


class ValidatePatchLinesError(SloppatchError):
    pass


def hunk_place_line_nmb(hunk: Hunk, file: SparsePatchFile, cfg: PatchConfig) -> LineNmb:
    """
    Returns line number and hunk original lines array
    """
    if not hunk.before_lines:
        return hunk.start_line

    file_lines_end = file.get_lines_end()
    range_begin, range_end = hunk_begin_line_range(hunk, file, cfg)

    line_nmb: LineNmb
    for line_nmb in spiral_range(hunk.start_line, range_begin, range_end):
        for i, hunk_line in enumerate(hunk.before_lines):
            line_in_file: LineNmb = line_nmb + i
            if line_in_file >= file_lines_end:
                break

            d = file.get_line_mask(line_in_file)
            if d is None:
                raise SloppatchInternalError(
                    f"Internal error. hunk_line_index, got None mask. Line number: {line_in_file}"
                )

            if d[1] != hunk_line.mask:
                break

        else:
            # Loop without errors -> ok
            return line_nmb

    raise ValidatePatchLinesError(
        "Unable to find hunk application line. "
        + f"Hunk: {hunk.str_header()}. "
        + f"Line range: ({range_begin}, {range_end})"
    )


def hunk_new_after_lines(
    hunk: Hunk, original_before_lines: List[str]
) -> List[AfterLine]:
    new_lines: List[AfterLine] = []
    original_line_idx = 0
    for c in hunk.changes:
        act = c.act
        match act:
            case RawAct.Delete:
                original_line_idx += 1
            case RawAct.Add:
                new_lines.append(
                    AfterLine(
                        line=c.line,
                        act=act,
                        original=None,
                        no_newline=c.no_newline if c.no_newline is not None else False,
                    )
                )
            case RawAct.Context:
                new_lines.append(
                    AfterLine(
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

    apply_line_idxs: List[LineNmb] = [-1] * len(patch)

    for i, hunk in enumerate(patch):
        nmb: LineNmb = hunk_place_line_nmb(hunk, file_cache, cfg)
        apply_line_idxs[i] = nmb

    # Validation: there must be no overlaps
    for i, (line_nmb, hunk) in enumerate(zip(apply_line_idxs, patch)):
        range_begin = line_nmb
        range_end = line_nmb + len(hunk.before_lines)

        for j in range(i + 1, len(patch)):
            inner_i = apply_line_idxs[j]
            inner_hunk = patch[j]

            inner_begin = inner_i
            inner_end = inner_i + len(inner_hunk.before_lines)

            if range_begin < inner_end and range_end > inner_begin:
                raise ValidatePatchLinesError(
                    "Hunks placement overlap. "
                    + f"Hunk1: {hunk.str_header()}, placement range: ({range_begin},{range_end}). "
                    + f"Hunk2: {inner_hunk.str_header()}, placement range: ({inner_begin},{inner_end})."
                )

    new_patch: List[PreparedHunk] = []
    for line_nmb, hunk in zip(apply_line_idxs, patch):
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


class ApplyPatchError(SloppatchError):
    pass


ChangesGroup = List[List[RawChange]]


def apply_patch(patch: PreparedPatch, lines_itr: Iterable[str]) -> Iterator[str]:
    """
    Returns line-by-line content of the file.
    We do not check the lines here. We assume, that they are the same as in file_cache
    """

    apply_line_nmbs = [hunk.begin_source_line for hunk in patch]

    # Application main loop
    line_nmb: LineNmb = -1
    skip_lines: int = 0
    applied_hunks: int = 0
    for i, line in enumerate(lines_itr):
        if skip_lines:
            skip_lines -= 1
            continue

        line_nmb = i + 1
        try:
            hunk_begin_idx = apply_line_nmbs.index(line_nmb)
        except ValueError:
            # Not found
            yield line
            continue

        cur_hunk = patch[hunk_begin_idx]
        # What if hunk contains 0 lines
        skip_lines = len(cur_hunk.before_lines) - 1
        applied_hunks += 1

        for line_data in cur_hunk.synced_after_lines:
            if line_data.original is not None:
                yield line_data.original
            else:
                yield_line = line_data.line
                if line_data.no_newline:
                    if yield_line and yield_line[-1] == "\n":
                        yield_line = yield_line[:-1]

                yield yield_line

        if skip_lines == -1:
            # Case, when Hunk contains only Add changes
            yield line

    expected_applied_hunks = len(patch)
    if applied_hunks != expected_applied_hunks:
        raise SloppatchInternalError(
            "Not all patches were applied. "
            + f"Expected: {expected_applied_hunks}, Applied: {applied_hunks}"
        )

    # We cannot do the check like that!
    # Check number of applied hunks instead
    # if line_idx != expected_lines:
    # raise ApplyPatchError(f"Mismatched number of lines. Read {line_idx}, expected {expected_lines}")
