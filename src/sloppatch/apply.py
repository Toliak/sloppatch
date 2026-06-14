import dataclasses
import enum
import itertools
import re
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
        if line_idx < first_line or line_idx >= last_line:
            continue

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


def hunk_line_index(hunk: PreparedHunk, file: SparsePatchFile, cfg: PatchConfig) -> int:
    """
    Returns line
    """
    file_lines_end = file.get_lines_end()
    range_begin, range_end = hunk_begin_line_range(hunk,file,cfg)

    # TODO: iterate over +0, -1, +1, -2, +2 etc..
    lines_to_check = itertools.chain(
        [hunk.before.line],
        range(range_begin, hunk.before.line - 1),
        range(hunk.before.line+1, range_end),
    )
    for line in lines_to_check:
        for i, hunk_line in enumerate(hunk.before_masks):
            file_line = line + i
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
        
        else:
            return line
        
    return -1

class ValidatePatchLinesError(SloppatchError):
    pass

# TODO: i don't like naming here. 
# It is not just a validator, it prepares the hunk positions based on the file's cache
def raise_validate_patch_lines(prepared_data: PreparePatchResult, cfg: PatchConfig) -> List[int]:
    """
    Validates patch. If something happens -- throws an error.
    Returns list of lines of beginnings of hunks. The same length as List[Hunk]
    """
    patch = prepared_data.patch
    file = prepared_data.file_cache

    apply_line_idxs = [-1] * len(patch)

    for i, hunk in enumerate(patch):
        idx = hunk_line_index(hunk, file, cfg)

        if idx == -1:
            range_begin, range_end = hunk_begin_line_range(hunk,file,cfg)
            raise ValidatePatchLinesError(
                "Unable to find hunk application line. "+
                f"Hunk: {hunk.str_header()}. "
                f"Line range: ({range_begin}, {range_end})"
            )
        
        apply_line_idxs[i] = idx
    
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

    return apply_line_idxs

class ApplyPatchError(SloppatchError):
    pass

def apply_patch(prepared_data: PreparePatchResult, cfg: PatchConfig, lines_itr: Iterable[str]) -> Iterator[str]:
    """
    Returns line-by-line content of the file.
    We do not check the lines here. We assume, that they are the same as in file_cache
    """
    @dataclasses.dataclass
    class CurHunk:
        hunk: PreparedHunk
        change_idx: int
        changes_after: List[RawChange]

    # Cache 
    changes_after_cache: List[List[RawChange]] = []
    for hunk in prepared_data.patch:
        changes_after = [
            c
            for c in hunk.changes
            if c.act.is_after()
        ]
        changes_after_cache.append(changes_after)

        # Verify lengths just in case
        assert len(hunk.before.lines) == len(hunk.before_masks)
        assert len(changes_after) == len(hunk.after.lines)

    # Get line numbers of every hunk
    apply_line_idxs = raise_validate_patch_lines(prepared_data, cfg)

    # Application main loop
    line_idx: int = -1
    cur_hunk: Optional[CurHunk] = None
    for i, line in enumerate(lines_itr):
        line_idx = i + 1
        if cur_hunk is None:
            try:
                hunk_begin_idx = apply_line_idxs.index(line_idx)
            except ValueError:
                # Not found
                yield line
                continue
            
            hunk = prepared_data.patch[hunk_begin_idx]
            cur_hunk = CurHunk(
                hunk=hunk,
                change_idx=0,
                changes_after=changes_after_cache[hunk_begin_idx],
            )
            assert len(cur_hunk.changes_after) == len(cur_hunk.hunk.after.lines)

        # cur_hunk is not None below

        change = cur_hunk.changes_after[cur_hunk.change_idx]
        if change.act == RawAct.Context:
            # We don't trust Context lines, 
            # because they may be in wrong case, with wrong spaces, etc...
            yield line
        else:
            yield cur_hunk.hunk.after.lines[cur_hunk.change_idx]

        cur_hunk.change_idx += 1
        if cur_hunk.change_idx == len(cur_hunk.changes_after):
            cur_hunk = None

    expected_lines = prepared_data.file_cache.get_lines_end()
    if line_idx != expected_lines - 1:
        raise ApplyPatchError(f"Mismatched number of lines. Read {line_idx}, expected {expected_lines}")

