from sloppatch.utils.sparse_file import SparsePatchFile, SparsePatchFileError
import pytest


class TestSparsePatchFileAddNewLine:
    @pytest.fixture
    def spf(self) -> SparsePatchFile:
        return SparsePatchFile()

    def test_first_line_creates_range(self, spf) -> None:
        spf.add_new_line(10, "hello", "HELLO")
        assert spf.get_line_mask(10) == ("hello", "HELLO")
        assert len(spf._ranges) == 1
        assert spf._ranges[0].line_start == 10

    def test_extend_last_range(self, spf) -> None:
        spf.add_new_line(10, "a", "A")
        spf.add_new_line(11, "b", "B")  # exactly after the last range end
        assert spf.get_line_mask(10) == ("a", "A")
        assert spf.get_line_mask(11) == ("b", "B")
        assert len(spf._ranges) == 1

    def test_create_new_range_after_gap(self, spf) -> None:
        spf.add_new_line(10, "a", "A")
        spf.add_new_line(15, "b", "B")  # gap, creates new range
        assert len(spf._ranges) == 2
        assert spf._ranges[0].line_start == 10
        assert spf._ranges[1].line_start == 15
        assert spf.get_line_mask(10) == ("a", "A")
        assert spf.get_line_mask(15) == ("b", "B")
        assert spf.get_line_mask(12) is None

    def test_collision_line_inside_existing_range(self, spf) -> None:
        spf.add_new_line(10, "a", "A")
        spf.add_new_line(11, "b", "B")  # extend to [10,12)
        with pytest.raises(SparsePatchFileError, match="Collision"):
            spf.add_new_line(10, "conflict", "C")

    def test_collision_before_last_range_start(self, spf) -> None:
        spf.add_new_line(20, "first", "F")
        with pytest.raises(SparsePatchFileError, match="before the last range"):
            spf.add_new_line(15, "early", "E")

    def test_multiple_ranges_no_collision(self, spf) -> None:
        spf.add_new_line(1, "a", "A")
        spf.add_new_line(3, "b", "B")
        spf.add_new_line(5, "c", "C")
        assert len(spf._ranges) == 3
