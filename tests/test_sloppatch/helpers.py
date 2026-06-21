from typing import List, Optional
from sloppatch.data import ParseConfig, Patch, PatchConfig, RawChange, RawAct, RawHunk
from sloppatch.parse import lines_to_raw_changes
from sloppatch.prepare import raw_patch_convert


def make_raw_hunk(
    before_line: int,
    before_len: int,
    after_line: int,
    after_len: int,
    comment: str = "",
    changes: Optional[List[RawChange]] = None,
) -> RawHunk:

    changes_list: List[RawChange]
    if changes is not None:
        changes_list = changes
    else:
        changes_list = []
        for i in range(before_line, before_line + before_len):
            changes_list.append(RawChange(RawAct.Delete, f"line original {i}"))
        for i in range(after_line, after_line + after_len):
            changes_list.append(RawChange(RawAct.Add, f"line new {i}"))

    return RawHunk(
        start_line=before_line,
        comment=comment,
        changes=changes_list,
    )


def make_change(act: RawAct, line: str) -> RawChange:
    return RawChange(act=act, line=line)


def raw_to_patch_convert_nocfg(raw: str) -> Patch:
    raw_patch = lines_to_raw_changes(raw)
    return raw_patch_convert(raw_patch, ParseConfig(), PatchConfig())
