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
