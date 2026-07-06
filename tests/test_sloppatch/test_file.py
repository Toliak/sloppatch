from typing import Iterator, List, Optional

import pytest

from sloppatch.config import ParseConfig, PatchConfig
from sloppatch.file import full_pipeline
from sloppatch.patch.apply import ApplyPatchError
from sloppatch.patch.prepare_by_file import ValidatePatchLinesError


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
        parse_config=ParseConfig(hunk_add_only_rule="apply", raw_empty_lines_rule='skip', raw_empty_hunk_rule='skip'),
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
    """

    # Missing context 8 and 13
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

    input_text_content = (
        "1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n11\n12\n13\n14\n15\n16\n17\n18\n"
    )

    expected_output_content = (
        "1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n11\n12_new\n13\n14\n15\n16\n17_new\n18\n"
    )

    # Configure to allow skipping up to 2 context lines
    config = PatchConfig(fuzz_context_lines=4, skip_context_lines=2, trim_string=True)

    output_iterator = _output_iterator(input_text_content, patch_content, cfg=config)

    new_text = "".join(output_iterator)
    assert new_text == expected_output_content

def test_full_pipeline_mixed_hunk() -> None:
    """
    Tests patch application when the input file is missing some context lines
    """

    # Missing context 8 and 13
    patch_content = """# 7 # Hunk expecting some missing context
=7

=8
# 16 # Empty
# 16 # Another hunk
=16
-17
+17_new
"""

    input_text_content = (
        "1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n11\n12_new\n13\n14\n15\n16\n17\n18\n"
    )

    expected_output_content = (
        "1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n11\n12_new\n13\n14\n15\n16\n17_new\n18\n"
    )

    # Configure to allow skipping up to 2 context lines
    config = PatchConfig(fuzz_context_lines=4, skip_context_lines=2, trim_string=True)

    output_iterator = _output_iterator(input_text_content, patch_content, cfg=config)

    new_text = "".join(output_iterator)
    assert new_text == expected_output_content


def test_full_pipeline_multiple_patches_with_same_begin_line_num() -> None:
    patch_content = """# 5 #
+Add line
# 5 #
+Add line2
"""
    input_text_content = "1\n2\n3\n4\n5\n6\n7"

    with pytest.raises(ValidatePatchLinesError, match="overlap"):
        _ = _output_iterator(input_text_content, patch_content, cfg=PatchConfig())


def test_full_pipeline_only_add_patch() -> None:
    patch_content = """# 5 #
+Add line
"""
    input_text_content = "1\n2\n3\n4\n5\n6\n7"

    output_iterator = _output_iterator(
        input_text_content, patch_content, cfg=PatchConfig()
    )

    new_text = "".join(output_iterator)
    assert new_text == "1\n2\n3\n4\nAdd line\n5\n6\n7"


def test_full_pipeline_only_add_patch_no_newline_in_text() -> None:
    patch_content = """# 7 #
=7
+Add line
/
"""
    input_text_content = "1\n2\n3\n4\n5\n6\n7"

    output_iterator = _output_iterator(
        input_text_content, patch_content, cfg=PatchConfig()
    )

    new_text = "".join(output_iterator)
    assert new_text == "1\n2\n3\n4\n5\n6\n7\nAdd line"


def test_full_pipeline_only_add_patch_on_eof() -> None:
    patch_content = """# 8 #
+Add line
/
"""
    input_text_content = "1\n2\n3\n4\n5\n6\n7"

    output_iterator = _output_iterator(
        input_text_content, patch_content, cfg=PatchConfig()
    )

    new_text = "".join(output_iterator)
    assert new_text == "1\n2\n3\n4\n5\n6\n7\nAdd line"


def test_full_pipeline_only_add_patch_on_eof_empty() -> None:
    patch_content = """# 1 #
+Add line
"""
    input_text_content = ""

    output_iterator = _output_iterator(
        input_text_content, patch_content, cfg=PatchConfig()
    )

    new_text = "".join(output_iterator)
    assert new_text == "Add line\n"


def test_full_pipeline_patch_with_EOF_line() -> None:
    patch_content = """# 500 #
+Add line
"""
    input_text_content = "1\n2\n3\n4\n5\n6\n7"

    output_iterator = _output_iterator(
        input_text_content, patch_content, cfg=PatchConfig()
    )

    with pytest.raises(ApplyPatchError, match="EOF"):
        _ = "".join(output_iterator)


def test_full_pipeline_skip_budget_total():
    cfg = PatchConfig(skip_context_lines=2)

    patch_content = """# 1 #
=A
=B
=C
=D
+z
/
"""

    input_text_content = """A
x
B
C
y
D
"""

    output_iterator = _output_iterator(input_text_content, patch_content, cfg=cfg)

    new_text = "".join(output_iterator)
    assert (
        new_text
        == """A
x
B
C
y
D
z"""
    )


def test_full_pipeline_skip_before_delete() -> None:
    """
    A delete line may be shifted forward by skipped context lines.
    The skipped line should remain in the output.
    """

    patch_content = """# 1 #
=A
-delete_me
=B
"""

    input_text_content = """A
extra_line
delete_me
B
"""

    expected_output_content = """A
extra_line
B
"""

    config = PatchConfig(
        skip_context_lines=1,
        trim_string=True,
    )

    output_iterator = _output_iterator(
        input_text_content,
        patch_content,
        cfg=config,
    )

    assert "".join(output_iterator) == expected_output_content


def test_full_pipeline_fuzzy_uses_nearest_duplicate_not_first() -> None:
    patch_content = """# 5 #
=foo
-bar
+BAR
"""

    input_text_content = (
        "foo\n"  # 1
        "bar\n"  # 2
        "x\n"
        "foo\n"  # 4 <-- nearest
        "bar\n"  # 5
        "foo\n"  # 6
        "bar\n"  # 7
    )

    expected_output_content = "foo\nbar\nx\nfoo\nBAR\nfoo\nbar\n"

    config = PatchConfig(
        fuzz_context_lines=3,
        trim_string=True,
    )

    output_iterator = _output_iterator(
        input_text_content,
        patch_content,
        cfg=config,
    )

    assert "".join(output_iterator) == expected_output_content
