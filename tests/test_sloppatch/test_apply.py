from typing import List
from sloppatch.apply import PatchConfig, apply_patch, hunk_line_index, prepare_hunk, prepare_patch, prepare_patch_lines
from sloppatch.data import Hunk, HunkData, Patch, RawAct, RawChange
import pytest

from sloppatch.parse import lines_to_raw_changes
from sloppatch.prepare import raw_patch_convert


class TestPreparePatch:
    @pytest.fixture
    def simple_patch(self) -> Patch:
        """A patch that changes line 3 from 'old' to 'new'."""
        return [
            Hunk(
                before=HunkData(line=3, lines=["old"]),
                after=HunkData(line=3, lines=["new"]),
                comment="",
                changes=[
                    RawChange(RawAct.Delete, "old\n"),
                    RawChange(RawAct.Add, "new\n"),
                ]
            )
        ]

    @pytest.fixture
    def first_line_patch(self) -> Patch:
        """A patch that changes line 3 from 'old' to 'new'."""
        return [
            Hunk(
                before=HunkData(line=1, lines=["old\n"]),
                after=HunkData(line=1, lines=["new1\n", "new2\n"]),
                comment="Testing",
                changes=[
                    RawChange(RawAct.Delete, "old\n"),
                    RawChange(RawAct.Add, "new1\n"),
                    RawChange(RawAct.Add, "new2\n"),
                ]
            )
        ]

    def test_empty_patch(self) -> None:
        cfg = PatchConfig(fuzz_context_lines=0)
        result = prepare_patch_lines([], cfg, [])
        assert result.patch == []
        assert result.line_ranges == []

    def test_patch_with_empty_hunk(self) -> None:
        cfg = PatchConfig(fuzz_context_lines=1)
        lines = [
            "line1\n", 
            "line2\n", 
            "line3\n", 
            "line4\n", 
            "line5\n"
        ]
        patch = prepare_patch([
            Hunk(
                before=HunkData(line=3, lines=[]),
                after=HunkData(line=3, lines=[]),
                comment="",
                changes=[],
            )
        ], cfg)
        result = prepare_patch_lines(patch, cfg, lines)

        assert result.patch == []
        assert result.line_ranges == []

    def test_fuzz_caches_surrounding_lines(self, simple_patch) -> None:
        cfg = PatchConfig(fuzz_context_lines=1)
        lines = [
            "line1\n", 
            "line2\n", 
            "line3\n", 
            "line4\n", 
            "line5\n"
        ]
        result = prepare_patch_lines(simple_patch, cfg, lines)

        # From 2 (incl) to 5 (excl)
        assert result.line_ranges == [(2, 5)]

        cache = result.file_cache
        assert cache.get_line_mask(2) == ("line2\n", "line2")  # only EOL trimming by default
        assert cache.get_line_mask(3) == ("line3\n", "line3")
        assert cache.get_line_mask(4) == ("line4\n", "line4")

        assert cache.get_line_mask(1) is None
        assert cache.get_line_mask(5) is None

        # Check something outside of the range
        assert cache.get_line_mask(999) is None

    def test_masks_respect_config(self, simple_patch) -> None:
        cfg = PatchConfig(fuzz_context_lines=2, trim_string=True, ignore_case_all=True)
        lines = [
            "  A  \n",      # 1
            "  b  \n",      # 2
            "  Old  \n",    # 3
            "  c  \n"       # 4
        ]
        result = prepare_patch_lines(simple_patch, cfg, lines)

        cache = result.file_cache
        assert cache.get_line_mask(1) == ("  A  \n", "a")
        assert cache.get_line_mask(2) == ("  b  \n", "b")
        assert cache.get_line_mask(3) == ("  Old  \n", "old")
        assert cache.get_line_mask(4) == ("  c  \n", "c")

    def test_ignore_whitespaces(self, first_line_patch) -> None:
        cfg = PatchConfig(fuzz_context_lines=1000, ignore_whitespaces=True)
        lines = [
            "a b\n",
            "o l d\n"
        ]
        result = prepare_patch_lines(first_line_patch, cfg, lines)
        # mask strips all whitespace
        cache = result.file_cache
        assert cache.get_line_mask(1) == ("a b\n", "ab")
        assert cache.get_line_mask(2) == ("o l d\n", "old")

    def test_prepared_hunk_has_masks(self, simple_patch: Patch) -> None:
        cfg = PatchConfig(trim_string=True)
        result = prepare_patch_lines(prepare_patch(simple_patch, cfg), cfg, [" old \n"])
        hunk = result.patch[0]
        assert hunk.before_masks == ["old"]

    def test_multiple_hunks(self) -> None:
        cfg = PatchConfig(fuzz_context_lines=0)
        patch = prepare_patch([
            Hunk(
                before=HunkData(line=2, lines=["x\n"]),
                after=HunkData(line=2, lines=["y\n"]),
                comment="",
                changes=[
                    RawChange(RawAct.Delete, "x\n"),
                    RawChange(RawAct.Add, "y\n"),
                ]
            ),
            Hunk(
                before=HunkData(line=5, lines=["z\n"]),
                after=HunkData(line=5, lines=["w\n"]),
                comment="",
                changes=[
                    RawChange(RawAct.Delete, "z\n"),
                    RawChange(RawAct.Add, "w\n"),
                ]
            ),
        ], cfg)
        lines = [
            "1\n", 
            "x\n", 
            "3\n", 
            "4\n", 
            "z\n",  
        ]
        result = prepare_patch_lines(patch, cfg, lines)
        # fuzz ranges: (2,3) and (5,6)
        assert len(result.line_ranges) == 2
        assert result.file_cache.get_line_mask(2) is not None
        assert result.file_cache.get_line_mask(5) == ('z\n', 'z')

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
        hunk = prepare_hunk(Hunk(
            before=HunkData(line=3, lines=["3\n"]),
            after=HunkData(line=3, lines=["3_1\n", "3_2\n"]),
            comment="",
            changes=[
                RawChange(RawAct.Delete, "3\n"),
                RawChange(RawAct.Add, "3_1\n"),
                RawChange(RawAct.Add, "3_2\n"),
            ]
        ), cfg)
        prepare_d = prepare_patch_lines([hunk], cfg, lines)
        idx = hunk_line_index(
            hunk=hunk,
            file=prepare_d.file_cache,
            cfg=cfg
        )

        assert idx == 3

    def test_line_before(self, lines, cfg) -> None:
        hunk = prepare_hunk(Hunk(
            before=HunkData(line=3, lines=["1"]),
            after=HunkData(line=3, lines=["1_1", "1_2"]),
            comment="",
            changes=[
                RawChange(RawAct.Delete, "1\n"),
                RawChange(RawAct.Add, "1_1\n"),
                RawChange(RawAct.Add, "1_2\n"),
            ]
        ), cfg)
        prepare_d = prepare_patch_lines([hunk], cfg, lines)
        idx = hunk_line_index(
            hunk=hunk,
            file=prepare_d.file_cache,
            cfg=cfg
        )

        assert idx == 1

    def test_line_after(self, lines, cfg) -> None:
        hunk = prepare_hunk(Hunk(
            before=HunkData(line=3, lines=["6"]),
            after=HunkData(line=3, lines=["6_1", "6_2"]),
            comment="",
            changes=[
                RawChange(RawAct.Delete, "6\n"),
                RawChange(RawAct.Add, "6_1\n"),
                RawChange(RawAct.Add, "6_2\n"),
            ]
        ), cfg)
        prepare_d = prepare_patch_lines([hunk], cfg, lines)
        idx = hunk_line_index(
            hunk=hunk,
            file=prepare_d.file_cache,
            cfg=cfg
        )

        assert idx == 6

    def test_not_found(self, lines, cfg) -> None:
        hunk = prepare_hunk(Hunk(
            before=HunkData(line=3, lines=["6", "000"]),
            after=HunkData(line=3, lines=["000", "000"]),
            comment="",
            changes=[
                RawChange(RawAct.Delete, "6\n"),
                RawChange(RawAct.Add, "000\n"),
                RawChange(RawAct.Context, "000\n"),
            ]
        ), cfg)
        prepare_d = prepare_patch_lines([hunk], cfg, lines)
        idx = hunk_line_index(
            hunk=hunk,
            file=prepare_d.file_cache,
            cfg=cfg
        )

        assert idx == -1
