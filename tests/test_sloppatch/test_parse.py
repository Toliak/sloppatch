from sloppatch.data import RawChange, RawAct, RawHunkData
from sloppatch.parse import LineParseError, lines_to_raw_changes
import pytest


class TestLinesToRawChanges:
    def test_empty_input(self):
        assert lines_to_raw_changes([]) == []

    def test_single_hunk_with_context_add_delete(self):
        lines = [
            "@@ -1,3 +1,4 @@ comment\n",
            " context1\n",
            "-removed\n",
            "+added\n",
            " context2\n",
        ]
        result = lines_to_raw_changes(iter(lines))
        assert len(result) == 1
        hunk = result[0]
        assert hunk.before == RawHunkData(line=1, length=3)
        assert hunk.after == RawHunkData(line=1, length=4)
        assert hunk.comment == " comment"
        expected_changes = [
            RawChange(RawAct.Context, "context1\n"),
            RawChange(RawAct.Delete, "removed\n"),
            RawChange(RawAct.Add, "added\n"),
            RawChange(RawAct.Context, "context2\n"),
        ]
        assert hunk.changes == expected_changes

    def test_multiple_hunks(self) -> None:
        lines = [
            "@@ -1,2 +1,2 @@\n",
            " a\n",
            " b\n",
            "@@ -5,1 +6,1 @@\n",
            "-x\n",
            "+y\n",
        ]
        result = lines_to_raw_changes(iter(lines))
        assert len(result) == 2
        assert result[0].before.line == 1
        assert result[0].before.length == 2
        assert result[1].before.line == 5
        assert result[1].before.length == 1
        assert len(result[0].changes) == 2
        assert len(result[1].changes) == 2

    def test_lines_without_trailing_newline(self) -> None:
        lines = [
            "@@ -1,1 +1,1 @@\n",
            " line\n",
        ]
        result = lines_to_raw_changes(iter(lines))
        assert len(result) == 1
        assert len(result[0].changes) == 1
        assert result[0].changes[0].line == "line\n"

    def test_line_with_no_newline_still_works(self) -> None:
        # The function strips \n if present, so a line without \n is fine.
        lines = ["@@ -1,1 +1,1 @@\n", " line"]
        result = lines_to_raw_changes(iter(lines))
        assert result[0].changes[0].line == "line"

    def test_change_without_hunk_raises(self) -> None:
        lines = ["-orphan change\n"]
        with pytest.raises(LineParseError, match="without hunk.+line 1"):
            lines_to_raw_changes(iter(lines))

    def test_unknown_format_raises(self) -> None:
        lines = ["@@ -1,1 +1,1 @@\n", "garbage\n"]
        with pytest.raises(LineParseError, match="Line 2.+wrong format"):
            lines_to_raw_changes(iter(lines))

    def test_hunk_start_without_length_raises_wrong_format(self) -> None:
        lines = ["@@ -1 +1 @@\n", " context\n"]
        with pytest.raises(LineParseError, match="Line 1.+wrong format"):
            lines_to_raw_changes(iter(lines))
