from typing import List
from sloppatch.apply import (
    PatchConfig,
    ValidatePatchLinesError,
    hunk_fuzzy_place_line_nmb,
    prepare_file_cache,
    spiral_range,
)
from sloppatch.data import ParseConfig, Patch, RawAct, RawChange, RawHunk
import pytest

from sloppatch.prepare import raw_patch_convert

from .helpers import raw_to_patch_convert_nocfg


class TestPreparePatch:
    @pytest.fixture
    def simple_patch(self) -> Patch:
        """A patch that changes line 3 from 'old' to 'new'."""
        raw = "# 3 #\n-old\n+new"
        return raw_to_patch_convert_nocfg(raw.splitlines(True))

    @pytest.fixture
    def first_line_patch(self) -> Patch:
        """A patch that changes line 3 from 'old' to 'new'."""
        raw = "# 1 # Testing\n-old\n+new1\n+new2\n/"
        return raw_to_patch_convert_nocfg(raw.splitlines(True))

    def test_empty_patch(self) -> None:
        cfg = PatchConfig(fuzz_context_lines=0)
        file = prepare_file_cache([], cfg, [])
        assert file._ranges == []

    def test_patch_with_empty_hunk(self) -> None:
        cfg = PatchConfig(fuzz_context_lines=1)
        lines = ["line1\n", "line2\n", "line3\n", "line4\n", "line5\n"]
        patch = raw_to_patch_convert_nocfg("")
        file = prepare_file_cache(patch, cfg, lines)

        assert file._ranges == []

    def test_fuzz_caches_surrounding_lines(self, simple_patch) -> None:
        cfg = PatchConfig(fuzz_context_lines=1)
        lines = ["line1\n", "line2\n", "line3\n", "line4\n", "line5\n"]
        file = prepare_file_cache(simple_patch, cfg, lines)

        assert file.get_line_mask(2) == (
            "line2\n",
            "line2",
        )  # only EOL trimming by default
        assert file.get_line_mask(3) == ("line3\n", "line3")
        assert file.get_line_mask(4) == ("line4\n", "line4")

        assert file.get_line_mask(1) is None
        assert file.get_line_mask(5) is None

        # Check something outside of the range
        assert file.get_line_mask(999) is None

    def test_masks_respect_config(self, simple_patch) -> None:
        cfg = PatchConfig(
            fuzz_context_lines=2, trim_string=True, ignore_case_rule="ignore-all"
        )
        lines = [
            "  A  \n",  # 1
            "  b  \n",  # 2
            "  Old  \n",  # 3
            "  c  \n",  # 4
        ]
        file = prepare_file_cache(simple_patch, cfg, lines)

        assert file.get_line_mask(1) == ("  A  \n", "a")
        assert file.get_line_mask(2) == ("  b  \n", "b")
        assert file.get_line_mask(3) == ("  Old  \n", "old")
        assert file.get_line_mask(4) == ("  c  \n", "c")

    def test_ignore_whitespaces(self, first_line_patch) -> None:
        cfg = PatchConfig(fuzz_context_lines=1000, ignore_whitespaces=True)
        lines = ["a b\n", "o l d\n"]
        file = prepare_file_cache(first_line_patch, cfg, lines)
        # mask strips all whitespace
        assert file.get_line_mask(1) == ("a b\n", "ab")
        assert file.get_line_mask(2) == ("o l d\n", "old")

    def test_prepared_hunk_has_masks(self, simple_patch: Patch) -> None:
        hunk = simple_patch[0]
        assert hunk.before_lines[0].mask == "old"

    def test_multiple_hunks(self) -> None:
        cfg = PatchConfig(fuzz_context_lines=0)
        raw1 = "# 2 #\n-x\n+y"
        raw2 = "# 5 #\n-z\n+x\n"
        patch = raw_to_patch_convert_nocfg((raw1 + "\n" + raw2).splitlines(True))
        lines = [
            "1\n",
            "x\n",
            "3\n",
            "4\n",
            "z\n",
        ]
        result = prepare_file_cache(patch, cfg, lines)
        assert result.get_line_mask(2) is not None
        assert result.get_line_mask(5) == ("z\n", "z")


class TestHunkLineIndex:
    @pytest.fixture
    def lines(self) -> List[str]:
        return [
            "1\n",
            "2\n",
            "3\n",
            "4\n",
            "5\n",
            "6\n",
        ]

    @pytest.fixture
    def cfg(self) -> PatchConfig:
        return PatchConfig(fuzz_context_lines=4)

    def test_correct_line(self, lines, cfg) -> None:
        patch = raw_patch_convert(
            [
                RawHunk(
                    start_line=3,
                    comment="",
                    changes=[
                        RawChange(RawAct.Delete, "3\n"),
                        RawChange(RawAct.Add, "3_1\n"),
                        RawChange(RawAct.Add, "3_2\n"),
                    ],
                )
            ],
            ParseConfig(),
            cfg,
        )
        file_cache = prepare_file_cache(patch, cfg, lines)
        idx = hunk_fuzzy_place_line_nmb(hunk=patch[0], file=file_cache, cfg=cfg)

        assert idx == 3

    def test_line_before(self, lines, cfg) -> None:
        patch = raw_patch_convert(
            [
                RawHunk(
                    start_line=3,
                    comment="",
                    changes=[
                        RawChange(RawAct.Delete, "1\n"),
                        RawChange(RawAct.Add, "1_1\n"),
                        RawChange(RawAct.Add, "1_2\n"),
                    ],
                )
            ],
            ParseConfig(),
            cfg,
        )
        file_cache = prepare_file_cache(patch, cfg, lines)
        idx = hunk_fuzzy_place_line_nmb(hunk=patch[0], file=file_cache, cfg=cfg)

        assert idx == 1

    def test_line_after(self, lines, cfg) -> None:
        patch = raw_patch_convert(
            [
                RawHunk(
                    start_line=3,
                    comment="",
                    changes=[
                        RawChange(RawAct.Delete, "6\n"),
                        RawChange(RawAct.Add, "6_1\n"),
                        RawChange(RawAct.Add, "6_2\n"),
                    ],
                )
            ],
            ParseConfig(),
            cfg,
        )
        file_cache = prepare_file_cache(patch, cfg, lines)
        idx = hunk_fuzzy_place_line_nmb(hunk=patch[0], file=file_cache, cfg=cfg)

        assert idx == 6

    def test_not_found(self, lines, cfg) -> None:
        patch = raw_patch_convert(
            [
                RawHunk(
                    start_line=3,
                    comment="",
                    changes=[
                        RawChange(RawAct.Delete, "6\n"),
                        RawChange(RawAct.Add, "000\n"),
                        RawChange(RawAct.Context, "000\n"),
                    ],
                )
            ],
            ParseConfig(),
            cfg,
        )
        file_cache = prepare_file_cache(patch, cfg, lines)
        with pytest.raises(ValidatePatchLinesError, match="Unable to find"):
            _ = hunk_fuzzy_place_line_nmb(hunk=patch[0], file=file_cache, cfg=cfg)


class TestSpiralRange:
    def test_spiral_range_basic(self):
        result = list(spiral_range(5, 0, 10))
        expected: List[int] = [5, 4, 6, 3, 7, 2, 8, 1, 9, 0]
        assert result == expected

    def test_spiral_range_edge_case_start_at_beginning(self):
        result = list(spiral_range(0, 0, 5))
        expected: List[int] = [0, 1, 2, 3, 4]
        assert result == expected

    def test_spiral_range_edge_case_start_at_end(self):
        result = list(spiral_range(4, 0, 5))
        expected: List[int] = [4, 3, 2, 1, 0]
        assert result == expected

    def test_spiral_range_single_element(self):
        result = list(spiral_range(5, 5, 6))
        expected: List[int] = [5]
        assert result == expected

    def test_spiral_range_invalid_start(self):
        result: List[int] = list(spiral_range(10, 0, 5))  # start outside range
        expected: List[int] = []
        assert result == expected

    def test_spiral_range_negative_numbers(self):
        result = list(spiral_range(-1, -3, 3))
        expected: List[int] = [-1, -2, 0, -3, 1, 2]
        assert result == expected

    def test_spiral_range_large_range(self):
        result = list(spiral_range(2, 0, 6))
        expected: List[int] = [2, 1, 3, 0, 4, 5]
        assert result == expected

    def test_spiral_range_empty_range(self):
        result = list(spiral_range(0, 0, 0))
        expected: List[int] = []
        assert result == expected
