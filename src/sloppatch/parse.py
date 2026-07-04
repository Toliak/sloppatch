"""
Raw text into the list of RawHunks.
Without knowledge of the target file.
"""

import dataclasses
import enum
import re
from typing import Iterable, List, Literal, Optional, assert_never

from .error import SloppatchError
from .data import LineNmb, RawAct, RawHunk, RawChange, RawPatch, ParseConfig

SLOP_DATA_HEADER: re.Pattern = re.compile(r"^[ ]+(\d+)[ ]+#(.*)$", re.DOTALL)
HEADER_FORMAT_VERBOSE = "# <START LINE NUMBER> # <COMMENT>"


class LineParseError(SloppatchError):
    pass


class LineType(enum.Enum):
    Delete = "-"
    Add = "+"
    Context = "="
    NoNewline = "/"
    Header = "#"


@dataclasses.dataclass
class Line:
    line_type: LineType
    data_line: str


def parse_line_type(line: str) -> Line:
    assert len(line) != 0
    first_char = line[0]

    for kv in LineType:
        if first_char == kv.value:
            return Line(
                line_type=kv,
                data_line=line[1:],
            )

    raise LineParseError(f"Unknown line format. First char: '{first_char}'")


def line_type_to_act(
    t: Literal[LineType.Delete, LineType.Add, LineType.Context],
) -> RawAct:
    match t:
        case LineType.Delete:
            return RawAct.Delete
        case LineType.Add:
            return RawAct.Add
        case LineType.Context:
            return RawAct.Context

    assert_never(t)


def lines_to_raw_changes(
    lines_itr: Iterable[str], cfg: Optional[ParseConfig] = None
) -> RawPatch:
    """
    Accept lines with '\n'
    """
    cfg_ready = cfg if cfg is not None else ParseConfig()

    result: List[RawHunk] = []
    for i, line in enumerate(lines_itr):
        line_nmb: LineNmb = i + 1
        if not line or line in ("\n", "\r\n", "\r"):
            match cfg_ready.raw_empty_lines_rule:
                case "skip":
                    continue
                case "as-empty-context-line":
                    line = "="
                case "strict":
                    raise LineParseError(f"Line {line_nmb}: empty")
                case _:
                    assert_never(cfg_ready.raw_empty_lines_rule)

        if cfg_ready.raw_line_ltrim_rule == "yes":
            line = line.lstrip()

        try:
            line_data = parse_line_type(line)
        except LineParseError as e:
            match cfg_ready.raw_wrong_format_lines_rule:
                case "skip":
                    continue
                case "strict":
                    raise LineParseError(f"Line {line_nmb}. " + str(e)) from e
            assert_never(cfg_ready.raw_wrong_format_lines_rule)

        line_type = line_data.line_type
        match line_type:
            case LineType.Delete | LineType.Add | LineType.Context:
                if not result:
                    match cfg_ready.raw_orphan_line_rule:
                        case "skip":
                            continue
                        case "strict":
                            raise LineParseError(
                                f"Line {line_nmb}. Change before Hunk header "
                                f"Line beginning: '{line[:32]}...'"
                            )
                    assert_never(cfg_ready.raw_orphan_line_rule)

                raw_change = RawChange(
                    act=line_type_to_act(line_type),
                    line=line_data.data_line,
                )
                result[-1].changes.append(raw_change)

            case LineType.NoNewline:
                if not result:
                    match cfg_ready.raw_orphan_line_rule:
                        case "skip":
                            continue
                        case "strict":
                            raise LineParseError(
                                f"Line {line_nmb}. NoNewline before Hunk header."
                            )
                    assert_never(cfg_ready.raw_orphan_line_rule)

                changes_ref = result[-1].changes
                if not changes_ref:
                    match cfg_ready.raw_orphan_nonewline_rule:
                        case "skip":
                            continue
                        case "strict":
                            raise LineParseError(
                                f"Line {line_nmb}. NoNewline without any Change lines before."
                            )
                    assert_never(cfg_ready.raw_orphan_nonewline_rule)

                last_ref = changes_ref[-1]
                changes_ref[-1] = RawChange(
                    act=last_ref.act, line=last_ref.line, no_newline=True
                )

            case LineType.Header:
                hdr_data_m = SLOP_DATA_HEADER.match(line_data.data_line)
                if hdr_data_m is None:
                    # Header parsing error, cannot skip
                    raise LineParseError(
                        f"Line {line_nmb}. "
                        + f"Wrong header's data format. Header line format: {HEADER_FORMAT_VERBOSE}. Got: '{line}'."
                    )

                hunk = RawHunk(
                    start_line=int(hdr_data_m.group(1)),
                    comment=hdr_data_m.group(2).strip(),
                    changes=[],
                )
                result.append(hunk)

            case _:
                assert_never(line_type)

    return result
