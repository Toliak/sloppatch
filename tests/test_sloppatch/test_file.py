from typing import Iterator, List
from sloppatch.apply import PatchConfig, apply_patch, hunk_line_index, prepare_hunk, prepare_patch, prepare_patch_lines
from sloppatch.data import Hunk, HunkData, Patch, RawAct, RawChange
import pytest

from sloppatch.file import full_pipeline
from sloppatch.parse import lines_to_raw_changes
from sloppatch.prepare import raw_patch_convert

def __list_iterator(l: List[str]) -> Iterator[str]:
    for item in l:
        yield item

def test_full_pipeline() -> None:
    patch = """@@ -3,3 +3,4 @@
 \t3
-4
+4_1
+4_2
 5
@@ -7,2 +8,2 @@
   7\t\t
-  8
+  8_1
"""
    text = "1\n2\n3\n4\n5\n6\n7\n8"
    text_lines = text.splitlines(True)
    patch_lines = patch.splitlines(True)

    output_iterator = full_pipeline(
        input_get_io=lambda: __list_iterator(text_lines),
        patch_io=__list_iterator(patch_lines),
        patch_config=PatchConfig(fuzz_context_lines=0, trim_string=True)
    )

    new_lines = list(output_iterator)

    new_text = "".join(new_lines)
    assert new_text == '1\n2\n3\n4_1\n4_2\n6\n7\n  8_1\n'
