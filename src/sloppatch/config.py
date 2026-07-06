import dataclasses
from typing import List, Literal, Optional


@dataclasses.dataclass
class ParseConfig:
    raw_empty_lines_rule: Literal["strict", "skip", "as-empty-context-line"] = "strict"
    """
    How to consider raw empty line in a hunk
    """

    raw_wrong_format_lines_rule: Literal["strict", "skip"] = "strict"
    """
    How to consider a line that starts with unknown character. Or has unknown format
    """

    raw_line_ltrim_rule: Literal["no", "yes"] = "no"
    """
    Trims the left side of the raw line.
    """

    raw_orphan_line_rule: Literal["strict", "skip"] = "strict"
    """
    What to do, if there are lines before the hunk beginning
    """

    raw_orphan_nonewline_rule: Literal["strict", "skip"] = "strict"
    """
    What to do, if there is NoNewLine line in empty hunk
    """

    raw_empty_hunk_rule: Literal["strict", "skip"] = "strict"
    """
    What to do with empty hunk
    """

    hunk_add_only_rule: Literal["apply", "reject"] = "reject"
    """
    What to do with the hunk, that contains only "Add" operations

    apply -- treat it as a valid hunk, apply it.
    reject -- raise an error.
    """


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

    ignore_case_rule: Literal["strict", "ignore-all"] = "strict"
    """
    strict -- do not ignore case.
    ignore-all -- Ignore case while matching any line.
    # ignore-context -- Ignore case while matching context lines.
    """

    skip_context_lines: int = 0
    """
    Maximum total number of lines that may be skipped while matching a single hunk.

    Skipped lines are searched only before **Context** and **Delete** actions.
    When skipped lines are encountered, they are treated as additional Context lines.
    """
