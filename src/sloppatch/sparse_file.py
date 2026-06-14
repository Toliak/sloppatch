import dataclasses
import enum
import functools
import re
from typing import Generator, Iterable, Iterator, List, Optional, Sequence, Tuple, Type
from .prepare import HunkData, Patch, Hunk

@dataclasses.dataclass
class FileRange:
    line_start: int
    lines: List[str]
    """
    Original lines
    """
    masks: List[str]
    """
    Prepared lines to find the hunks
    """

    def get_line_end(self) -> int:
        return self.line_start + len(self.lines)
    
    def get_local_idx(self, global_idx: int) -> int:
        return global_idx - self.line_start

class SparsePatchFileError(RuntimeError):
    pass

class SparsePatchFile:
    def __init__(self) -> None:
        self._ranges: List[FileRange] = []

    def add_new_line(self, line_idx: int, line: str, mask: str):
        """
        This function supports: 
        - appending line to the last existing range
        - creating a new range
        """

        self.get_line_mask.cache_clear()
        self.get_lines_end.cache_clear()

        ranges_len = len(self._ranges)
        if ranges_len != 0:
            last_range = self._ranges[ranges_len - 1]
            r_start = last_range.line_start
            r_end = last_range.get_line_end()
            if r_end == line_idx:
                # Add the line to the range
                last_range.lines.append(line)
                last_range.masks.append(mask)
                return
            
            if r_start <= line_idx < r_end:
                raise SparsePatchFileError(
                    "Collision, unable to add new line. " +
                    f"line_idx={line_idx} range=({r_start}, {r_end})"
                )
            
            if line_idx < r_start:
                raise SparsePatchFileError(
                    "Collision, unable to add new line before the last range. " +
                    f"line_idx={line_idx} range=({r_start}, {r_end})"
                )
            
        # line_idx > r_end
        self._ranges.append(FileRange(
            line_start=line_idx,
            lines=[line],
            masks=[mask]
        ))

    @functools.lru_cache(maxsize=1024)
    def get_line_mask(self, line_idx: int) -> Optional[Tuple[str, str]]:
        """
        Returns line and its mask
        """
        for r in self._ranges:
            r_start = r.line_start
            r_end = r.get_line_end()

            if not (r_start <= line_idx < r_end):
                continue
            
            idx = r.get_local_idx(line_idx)
            return (r.lines[idx], r.masks[idx])

        return None

    @functools.lru_cache()
    def get_lines_end(self) -> int:
        """
        The last line number (exclusively, counts from 1)
        """
        if not self._ranges:
            return 0

        return max(
            r.get_line_end()
            for r in self._ranges
        )
    
    def is_empty(self) -> bool:
        return not self._ranges

    # def add_line(self, line_idx: int, line: str, mask: str):
    #     # Here we assume that the lines will be appended more often
    #     for r in reversed(self._ranges):
    #         r_start = r.line_start
    #         r_end = r.line_start + len(r.lines)

    #         # Line change
    #         if r_start <= line_idx < r_end:
    #             idx = line_idx - r_start
    #             r.lines[idx] = line
    #             r.masks[idx] = mask
    #             return

    #         # Line add into the existing r
    #         if 

        # New range

        # validate that there is no ranges that overhang
        # we cannot add the lines in the middle 
