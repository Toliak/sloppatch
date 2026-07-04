"""
Patch into the PreparedPatch (with the file knowledge).
Applying to the file.
"""

from typing import Iterable, Iterator, List, Optional, Tuple, assert_never

from .data import (
    AfterLine,
    BeforeLine,
    HunkLine,
    LineNmb,
    PatchConfig,
    PreparedHunk,
    PreparedPatch,
    RawAct,
    RawChange,
    RawHunk,
    RawHunkChanges,
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
        end_line = hunk.start_line + len(hunk.before_lines) + cfg.fuzz_context_lines + cfg.skip_context_lines
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

def hunk_place_at_line(hunk: Hunk, file: SparsePatchFile, line_nmb: LineNmb, cfg: PatchConfig) -> Optional[Hunk]:
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

    for raw_change in hunk.changes:
        match raw_change.act:
            case RawAct.Add:
                new_raw_changes.append(raw_change)
                new_after_lines.append(hunk.after_lines[after_lines_i])
                after_lines_i += 1
                
            case RawAct.Delete:
                hunk_line = hunk.before_lines[before_lines_i]
                line_in_file: LineNmb = line_nmb + before_lines_i + skip_context_offset

                line_found: bool = False
                skipped_lines: List[Tuple[str, str]] = []

                for skip_i in range(0, (cfg.skip_context_lines - skip_context_offset) + 1):
                    d = file.get_line_mask(line_in_file + skip_i)
                    if d is None:
                        # End of file or file cached fragment
                        return None

                    _file_line_raw, file_line_mask = d
                    if file_line_mask != hunk_line.mask:
                        skipped_lines.append(d)
                    else:
                        line_found = True
                        break
            
                if line_found is False:
                    return None
        
                for d in skipped_lines:
                    new_raw_changes.append(RawChange(
                        RawAct.Context,
                        d[0]
                    ))
                    new_before_lines.append(BeforeLine(
                        d[0],
                        RawAct.Context,
                        d[1]
                    ))
                    new_after_lines.append(HunkLine(
                        d[0],
                        RawAct.Context,
                    ))

                new_raw_changes.append(raw_change)
                new_before_lines.append(hunk_line)
                skip_context_offset += len(skipped_lines)
                before_lines_i += 1
                pass

            case RawAct.Context:
                hunk_line = hunk.before_lines[before_lines_i]
                line_in_file = line_nmb + before_lines_i + skip_context_offset

                line_found = False
                skipped_lines = [] # List[Tuple[str, str]]

                for skip_i in range(0, (cfg.skip_context_lines - skip_context_offset) + 1):
                    d = file.get_line_mask(line_in_file + skip_i)
                    if d is None:
                        # End of file or file cached fragment
                        return None

                    _file_line_raw, file_line_mask = d
                    if file_line_mask != hunk_line.mask:
                        skipped_lines.append(d)
                    else:
                        line_found = True
                        break
            
                if line_found is False:
                    return None
        
                for d in skipped_lines:
                    new_raw_changes.append(RawChange(
                        RawAct.Context,
                        d[0]
                    ))
                    new_before_lines.append(BeforeLine(
                        d[0],
                        RawAct.Context,
                        d[1]
                    ))
                    new_after_lines.append(HunkLine(
                        d[0],
                        RawAct.Context,
                    ))

                new_raw_changes.append(raw_change)
                new_before_lines.append(hunk_line)
                new_after_lines.append(hunk_line)
                skip_context_offset += len(skipped_lines)
                before_lines_i += 1
                after_lines_i += 1
                pass

            case _:
                assert_never(raw_change.act)

    return Hunk(
        start_line=hunk.start_line,
        comment=hunk.comment,
        changes=new_raw_changes,
        before_lines=new_before_lines,
        after_lines=new_after_lines,
    )

def hunk_fuzzy_place_line_nmb(hunk: Hunk, file: SparsePatchFile, cfg: PatchConfig) -> Tuple[LineNmb, Hunk]:
    """
    The core function, that detects the Hunk's line number.

    Returns line number of the Hunk beginning
    """
    if not hunk.before_lines:
        return hunk.start_line, hunk

    range_begin, range_end = hunk_begin_line_range(hunk, file, cfg)

    line_nmb: LineNmb
    for line_nmb in spiral_range(hunk.start_line, range_begin, range_end):
        r = hunk_place_at_line(hunk, file, line_nmb, cfg)
        if r is not None:
            return line_nmb, r

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

    apply_line_idxs: List[LineNmb] = []
    patch_placed: Patch = []

    for i, hunk in enumerate(patch):
        line_nmb, new_hunk = hunk_fuzzy_place_line_nmb(hunk, file_cache, cfg)
        apply_line_idxs.append(line_nmb)
        patch_placed.append(new_hunk)

    assert len(apply_line_idxs) == len(patch) == len(patch_placed)

    # Validation: there must be no overlaps
    for i, (line_nmb, hunk) in enumerate(zip(apply_line_idxs, patch_placed)):
        range_begin = line_nmb      # incl
        range_end = line_nmb + len(hunk.before_lines)       # excl
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


class ApplyPatchError(SloppatchError):
    pass


def _synced_after_lines_gen(synced_after_lines: List[AfterLine]) -> Iterator[str]:
    """Helper generator to yield the resulting lines for a hunk's `synced_after_lines`."""
    for i, line_data in enumerate(synced_after_lines):
        if line_data.original is not None:
            line = line_data.original

            if (
                line_data.act == RawAct.Context 
                and not (line.endswith("\n")) 
                and i + 1 < len(synced_after_lines) 
                and synced_after_lines[i+1].act == RawAct.Add
            ):
                # Edge-case: end of file without EOL. And +Add after it
                yield line_data.original + '\n'
            else:
                yield line_data.original
        else:
            yield_line = line_data.line
            if line_data.no_newline:
                if yield_line and yield_line[-1] == "\n":
                    yield_line = yield_line[:-1]
            yield yield_line

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
    i: int = -1     # because we can receive empty file (without any lines)
    for i, line in enumerate(lines_itr):
        assert skip_lines >= 0
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

        yield from _synced_after_lines_gen(cur_hunk.synced_after_lines)

        if skip_lines == -1:
            skip_lines = 0
            # Case, when Hunk contains only Add changes
            yield line

    total_file_lines: LineNmb = i + 1
    try:
        hunk_begin_idx = apply_line_nmbs.index(total_file_lines + 1)
    except ValueError:
        # Not found
        pass
    else:
        cur_hunk = patch[hunk_begin_idx]
        if not cur_hunk.before_lines:
            # Add-only hunk
            if total_file_lines != 0:
                # Not empty file
                raise ApplyPatchError(
                    "Unable to apply hunk. Add-only hunk must contain at least one context line for non-empty file"
                    + f"Hunk: {cur_hunk.str_header()}, file total lines: {total_file_lines}"
                )
        
            # Edge-case: hunk with add-only for empty file
            yield from _synced_after_lines_gen(cur_hunk.synced_after_lines)
            applied_hunks += 1

    for j, line_nmb in enumerate(reversed(apply_line_nmbs)):
        i = len(apply_line_nmbs) - 1 - j
        if line_nmb <= total_file_lines + 1:
            break
        
        hunk = patch[i]
        raise ApplyPatchError(
            "Unable to apply hunk (EOF). "
            + f"Hunk: {hunk.str_header()}, file total lines: {total_file_lines}"
        )

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
