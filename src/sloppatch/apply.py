import dataclasses
import enum
import itertools
import re
import sys
from typing import Generator, Iterable, Iterator, List, Optional, Sequence, Tuple, Type

from .data import RawAct, RawChange
from .error import SloppatchError, SloppatchInternalError
from .sparse_file import SparsePatchFile
from .prepare import HunkData, Patch, Hunk


@dataclasses.dataclass
class PatchConfig:
    fuzz_context_lines: int = 0
    """
    How many lines before/after can we search to get the real patch location
    """
    trim_string: bool = False
    """
    Trim the string while matching
    """
    ignore_whitespaces: bool = False
    """
    Completely ignore whitespaces while matching.
    When enabled, `trim_string` is automatically set to True.
    """

    # TODO: implement
    __ignore_case_context: bool = False
    """
    Ignore case while matching context lines
    """

    ignore_case_all: bool = False
    """
    Ignore case while matching any line.
    When enabled, `trim_string` is automatically set to True.
    """

ANY_WHITESPACE_RE = re.compile(r"\s+")

def _line_to_mask(line: str, cfg: PatchConfig) -> str:
    if not line:
        return line

    new_line = line
    if new_line[-1] == '\n':
        new_line = new_line[:-1]

    if cfg.ignore_whitespaces:
        new_line = re.sub(ANY_WHITESPACE_RE, "", new_line)

    if cfg.trim_string and not cfg.ignore_whitespaces:
        new_line = new_line.strip()

    if cfg.ignore_case_all:
        new_line = new_line.lower()

    return new_line

def _is_line_in_ranges(idx: int, range_list: List[Tuple[int, int]]) -> bool:
    for r in range_list:
        if r[0] <= idx < r[1]:
            return True
        
    return False

@dataclasses.dataclass
class PreparedHunkData(HunkData):
    masks: List[str]

@dataclasses.dataclass
class PreparedHunk(Hunk):
    before_masks: List[str]


PreparedPatch = List[PreparedHunk]


@dataclasses.dataclass
class PreparePatchResult:
    patch: PreparedPatch
    """
    Does not contain empty hunks
    """

    line_ranges: List[Tuple[int, int]]
    """
    The beginning included, the end is excluded
    """

    file_cache: SparsePatchFile

def prepare_hunk(hunk: Hunk, cfg: PatchConfig) -> PreparedHunk:
    lines = hunk.before.lines
    return PreparedHunk(
        before_masks=[
            _line_to_mask(line, cfg)
            for line in lines
        ],

        before=hunk.before,
        after=hunk.after,
        comment=hunk.comment,
        changes=hunk.changes,
    )

def prepare_patch(patch: Patch, cfg: PatchConfig) -> PreparedPatch:
    result_patch: PreparedPatch = []
    for hunk in patch:
        if len(hunk.before.lines) == 0 and len(hunk.after.lines) == 0:
            continue

        result_patch.append(prepare_hunk(hunk, cfg))

    return result_patch

def prepare_patch_lines(patch: PreparedPatch, cfg: PatchConfig, lines_itr: Iterable[str]) -> PreparePatchResult:
    """
    Prepares data for patch

    Accepts lines_itr with '\n' at the end
    """

    if len(patch) == 0:
        return PreparePatchResult(
            patch=[],
            line_ranges=[],
            file_cache=SparsePatchFile(),
        )

    fuzz_line_ranges: List[Tuple[int, int]] = []
    for hunk in patch:
        start_line = max(hunk.before.line - cfg.fuzz_context_lines, 0)
        end_line = hunk.before.line + len(hunk.before.lines) + cfg.fuzz_context_lines
        fuzz_line_ranges.append((start_line, end_line))

    first_line = min(v[0] for v in fuzz_line_ranges)
    last_line = max(v[1] for v in fuzz_line_ranges)
    
    file_cache = SparsePatchFile()
    # Here we cache the lines by their "masks" with regards to the `cfg``
    line_idx = 0
    for line in lines_itr:
        line_idx += 1   # Patch numerates lines from 1
        if line_idx < first_line:
            continue
        if line_idx >= last_line:
            break

        if _is_line_in_ranges(line_idx, fuzz_line_ranges):
            mask = _line_to_mask(line, cfg)
            file_cache.add_new_line(line_idx, line, mask)

    return PreparePatchResult(
        patch=patch,
        line_ranges=fuzz_line_ranges,
        file_cache=file_cache,
    )

def hunk_begin_line_range(hunk: PreparedHunk, file: SparsePatchFile, cfg: PatchConfig) -> Tuple[int, int]:
    file_lines_end = file.get_lines_end()
    return (
        max(hunk.before.line - cfg.fuzz_context_lines, 1),
        min(hunk.before.line + cfg.fuzz_context_lines, file_lines_end),
    )


def hunk_line_index(hunk: PreparedHunk, file: SparsePatchFile, cfg: PatchConfig) -> Tuple[int, List[str]]:
    """
    Returns line number and hunk original lines array
    """
    file_lines_end = file.get_lines_end()
    range_begin, range_end = hunk_begin_line_range(hunk,file,cfg)

    # TODO: iterate over +0, -1, +1, -2, +2 etc..
    lines_to_check = itertools.chain(
        [hunk.before.line],
        range(range_begin, hunk.before.line - 1),
        range(hunk.before.line+1, range_end),
    )
    original_lines: List[str] = []
    for line_idx in lines_to_check:
        original_lines = []

        for i, hunk_line in enumerate(hunk.before_masks):
            file_line = line_idx + i
            if file_line >= file_lines_end:
                break

            d = file.get_line_mask(file_line)
            if d is None:
                raise SloppatchInternalError(
                    "Internal error. hunk_line_index, got None mask. "
                    f"Line: {file_line}"
                )

            if d[1] != hunk_line:
                break
            original_lines.append(d[0])
        
        else:
            return line_idx, original_lines
        
    return -1, []

class ValidatePatchLinesError(SloppatchError):
    pass

def hunk_new_after_lines(hunk: Hunk, original_before_lines: List[str]) -> List[str]:
    new_lines: List[str] = []
    original_line_idx = 0
    for c in hunk.changes:
        if c.act == RawAct.Delete:
            original_line_idx += 1
            continue
        if c.act == RawAct.Add:
            new_lines.append(c.line)
            continue
        if c.act == RawAct.Context:
            new_lines.append(
                original_before_lines[original_line_idx]
            )
            original_line_idx += 1
            continue
    
    return new_lines

# TODO: i don't like naming here. 
# It is not just a validator, it prepares the hunk positions based on the file's cache
def raise_validate_patch_lines(prepared_data: PreparePatchResult, cfg: PatchConfig) -> Tuple[List[int], List[List[str]]]:
    """
    Validates patch. If something happens -- throws an error.
    Returns list of lines of beginnings of hunks. The same length as List[Hunk]
    """
    patch = prepared_data.patch
    file = prepared_data.file_cache

    apply_line_idxs = [-1] * len(patch)
    new_after_lines_list: List[List[str]] = [[]] * len(patch)

    for i, hunk in enumerate(patch):
        idx, original_lines = hunk_line_index(hunk, file, cfg)

        if idx == -1:
            range_begin, range_end = hunk_begin_line_range(hunk, file, cfg)
            raise ValidatePatchLinesError(
                "Unable to find hunk application line. "+
                f"Hunk: {hunk.str_header()}. "
                f"Line range: ({range_begin}, {range_end})"
            )
        
        apply_line_idxs[i] = idx
        new_after_lines_list[i] = hunk_new_after_lines(hunk, original_lines)
    
    for i, (line_i, hunk) in enumerate(zip(apply_line_idxs, patch)):
        range_begin = line_i
        range_end = line_i + len(hunk.before.lines)

        for j in range(i+1, len(patch)):
            inner_i = apply_line_idxs[j]
            inner_hunk = patch[j]

            inner_begin = inner_i
            inner_end = inner_i + len(inner_hunk.before.lines)

            if range_begin < inner_end and range_end > inner_begin:
                raise ValidatePatchLinesError(
                    "Hunks placement overlap. "+
                    f"Hunk1: {hunk.str_header()}, placement range: ({range_begin},{range_end}). " +
                    f"Hunk2: {inner_hunk.str_header()}, placement range: ({inner_begin},{inner_end})."
                )

    return apply_line_idxs, new_after_lines_list

class ApplyPatchError(SloppatchError):
    pass


ChangesGroup = List[List[RawChange]]

def apply_patch(prepared_data: PreparePatchResult, cfg: PatchConfig, lines_itr: Iterable[str]) -> Iterator[str]:
    """
    Returns line-by-line content of the file.
    We do not check the lines here. We assume, that they are the same as in file_cache
    """
    @dataclasses.dataclass
    class CurHunk:
        hunk: PreparedHunk
        change_idx: int
        # changes_group: ChangesGroup
        # """
        # Grouped changes by line. 
        # The first element must be Delete, Context or Add (if Add is the first change).
        # Next elements must be Add (if presented)
        # """

        new_after_lines: List[str]

    # Cache 
    changes_after_cache: List[ChangesGroup] = []
    for hunk in prepared_data.patch:
        changes_after: ChangesGroup = []
        # Assume that PreparedPatch does not contain empty Hunks
        for c in hunk.changes:
            if c.act.is_before():
                changes_after.append([c])
            else:   # c.act == RawAct.Add
                if not changes_after:   # If the Add is the first line
                    # TODO: check that the Add is not the first in the Hunk!!!!
                    changes_after.append([])
                changes_after[-1].append(c)

        changes_after_cache.append(changes_after)

        # Verify lengths just in case
        assert len(hunk.before.lines) == len(hunk.before_masks)
        assert 0 <= len(changes_after) - len(hunk.before.lines) <= 1

    # Get line numbers of every hunk
    apply_line_idxs, ready_after_lines = raise_validate_patch_lines(prepared_data, cfg)
    assert len(ready_after_lines) == len(ready_after_lines)
    assert len(apply_line_idxs) == len(prepared_data.patch)

    # Application main loop
    line_idx: int = -1
    skip_lines: int = 0
    applied_hunks: int = 0
    for i, line in enumerate(lines_itr):
        if skip_lines:
            skip_lines -= 1
            continue

        line_idx = i + 1
        try:
            hunk_begin_idx = apply_line_idxs.index(line_idx)
        except ValueError:
            # Not found
            yield line
            continue
        
        cur_hunk = prepared_data.patch[hunk_begin_idx]
        new_after_lines=ready_after_lines[hunk_begin_idx]
        # What if hunk contains 0 lines
        skip_lines = len(cur_hunk.before.lines) - 1
        applied_hunks += 1

        for new_line in new_after_lines:
            yield new_line

        if skip_lines == -1:
            # Case, when Hunk contains only Add changes
            yield line


    expected_applied_hunks = len(prepared_data.patch)
    if applied_hunks != expected_applied_hunks:
        raise SloppatchInternalError("Not all patches were applied. " +
                                     f"Expected: {expected_applied_hunks}, Applied: {applied_hunks}")

    # We cannot do the check like that!
    # Check number of applied hunks instead
    # if line_idx != expected_lines:
        # raise ApplyPatchError(f"Mismatched number of lines. Read {line_idx}, expected {expected_lines}")

