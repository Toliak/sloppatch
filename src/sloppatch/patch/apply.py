"""
Patch, Stage 4.

Apply the PreparedPatch to the file content.
"""

from typing import Iterable, Iterator, List

from .prepare_by_file_data import PreparedAfterLine, PreparedPatch
from .raw_parse_data import RawAct
from ..utils.types import LineNmb
from ..error import SloppatchError, SloppatchInternalError
from ..utils.misc import str_ends_with_eol


class ApplyPatchError(SloppatchError):
    pass


def _synced_after_lines_gen(synced_after_lines: List[PreparedAfterLine]) -> Iterator[str]:
    """Helper generator to yield the resulting lines for a hunk's `synced_after_lines`."""
    for i, line_data in enumerate(synced_after_lines):
        if line_data.original is not None:
            line = line_data.original

            if (
                line_data.act == RawAct.Context
                and not str_ends_with_eol(line)
                and i + 1 < len(synced_after_lines)
                and synced_after_lines[i + 1].act == RawAct.Add
            ):
                # Edge-case: end of file without EOL. And +Add after it
                yield line_data.original + "\n"
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
    We do not check the lines here. We assume, that they are the same as in file_cache.

    Each returned string contains EOL. Do not need to add anything on Joining
    """

    apply_line_nmbs = [hunk.begin_source_line for hunk in patch]

    # Application main loop
    line_nmb: LineNmb = -1
    skip_lines: int = 0
    applied_hunks: int = 0
    i: int = -1  # because we can receive empty file (without any lines)
    last_yielded_line: str = ""
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
            last_yielded_line = line
            yield line
            continue

        cur_hunk = patch[hunk_begin_idx]
        # What if hunk contains 0 lines
        skip_lines = len(cur_hunk.before_lines) - 1
        applied_hunks += 1

        for line_to_yield in _synced_after_lines_gen(cur_hunk.synced_after_lines):
            last_yielded_line = line_to_yield
            yield line_to_yield

        if skip_lines == -1:
            # Case, when Hunk contains only Add changes
            skip_lines = 0
            last_yielded_line = line
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
            # Add-only hunk. Edge-case: "Append to the file" action
            if total_file_lines != 0 and not last_yielded_line.endswith("\n"):
                yield "\n"

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
