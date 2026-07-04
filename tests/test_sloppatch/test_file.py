from typing import Iterator, List, Optional
from sloppatch.apply import (
    PatchConfig,
)

from sloppatch.file import full_pipeline


def _list_iterator(item_list: List[str]) -> Iterator[str]:
    for item in item_list:
        yield item


def _output_iterator(
    input_text: str,
    patch: str,
    cfg: Optional[PatchConfig] = None,
):
    cfg_ready = (
        cfg if cfg is not None else PatchConfig(fuzz_context_lines=0, trim_string=True)
    )
    text_lines = input_text.splitlines(True)
    patch_lines = patch.splitlines(True)

    return full_pipeline(
        input_get_io=lambda: _list_iterator(text_lines),
        patch_io=_list_iterator(patch_lines),
        patch_config=cfg_ready,
    )


def test_full_pipeline() -> None:
    patch = """# 3 # First hunk
=\t3
-4
+4_1
+4_2
=5
# 7 #
=    7\t\t
-  8
+  8_1
/
"""
    text = "1\n2\n3\n4\n5\n6\n7\n8"

    output_iterator = _output_iterator(text, patch)

    new_text = "".join(output_iterator)
    assert new_text == "1\n2\n3\n4_1\n4_2\n5\n6\n7\n  8_1"


def test_full_pipeline_back_to_back_patch() -> None:
    patch = """# 3 #
=3
-4
=5
# 6 #
=6
-7
+7_1
"""
    text = "1\n2\n3\n4\n5\n6\n7\n8"

    output_iterator = _output_iterator(text, patch)

    new_text = "".join(output_iterator)
    assert new_text == "1\n2\n3\n5\n6\n7_1\n8"


def test_full_pipeline_hunk_starts_from_add() -> None:
    patch = """# 1 #
+0
=1
=2
"""
    text = "1\n2\n3\n4\n5\n6\n7\n8"

    output_iterator = _output_iterator(text, patch)

    new_text = "".join(output_iterator)
    assert new_text == "0\n1\n2\n3\n4\n5\n6\n7\n8"


def test_full_pipeline_hunk_starts_from_add2() -> None:
    patch = """# 1 #
+0
"""
    text = "1"

    output_iterator = _output_iterator(text, patch)

    new_text = "".join(output_iterator)
    assert new_text == "0\n1"


def test_full_pipeline_skip_context_lines() -> None:
    """
    Tests patch application when the input file is missing some context lines
    that the patch specifies, using the skip_context_lines feature.
    The patch expects lines 3, 9, 10, 11, 15, but the input file has gaps (missing 9, 10).
    With skip_context_lines=2, the matcher should tolerate missing up to 2 consecutive
    expected context lines before giving up.
    """
    # The patch expects context lines 3, 9, 10, 11, 15
    patch_content = """# 7 # Hunk expecting some missing context
=7
=9
=10
=11
-12
+12_new
=14
# 16 # Another hunk
=16
-17
+17_new
"""
    
    # Input file is missing lines 9 and 10 compared to the patch's expectation.
    # Line numbers effectively become: 1, 2, 3, 4, 5, 6, 7, 8, 11, 12, 13, 14, 15, 16, 17, 18
    # So the hunk should find line 3, then skip 9/10, find 11, match/delete 12 (-> 11 in file), 
    # add 12_new, and find 15 (-> 13 in file).
    # The second hunk finds 16 (-> 14 in file), deletes 17 (-> 15 in file), adds 17_new.
    input_text_content = "1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n11\n12\n13\n14\n15\n16\n17\n18\n"

    expected_output_content = "1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n11\n12_new\n13\n14\n15\n16\n17_new\n18\n"

    # Configure to allow skipping up to 2 context lines
    config = PatchConfig(fuzz_context_lines=4, skip_context_lines=2, trim_string=True)

    output_iterator = _output_iterator(input_text_content, patch_content, cfg=config)

    new_text = "".join(output_iterator)
    print(f"Input:\n{input_text_content}")
    print(f"Patch:\n{patch_content}")
    print(f"Expected:\n{expected_output_content}")
    print(f"Actual:\n{new_text}")
    assert new_text == expected_output_content, \
        f"Patch application failed with missing context lines. Expected:\n{expected_output_content}\nGot:\n{new_text}"
