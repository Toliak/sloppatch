import re
from sloppatch.config import PatchConfig
from sloppatch.utils.misc import ANY_WHITESPACE_RE
from typing import List, Optional, Tuple, assert_never


def line_to_mask(line: str, cfg: PatchConfig) -> str:
    if not line:
        return line

    new_line = line
    if new_line[-1] == "\n":
        new_line = new_line[:-1]

    if cfg.ignore_whitespaces:
        new_line = re.sub(ANY_WHITESPACE_RE, "", new_line)

    if cfg.trim_string and not cfg.ignore_whitespaces:
        new_line = new_line.strip()

    match cfg.ignore_case_rule:
        case "strict":
            pass  # do noting
        case "ignore-all":
            new_line = new_line.lower()
        # case 'ignore-context':
        #     if act == RawAct.Context:
        #         new_line = new_line.lower()
        case _:
            assert_never(cfg.ignore_case_rule)

    return new_line
