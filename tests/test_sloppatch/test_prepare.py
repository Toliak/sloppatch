from sloppatch.data import RawAct
import pytest
from sloppatch.data import ParseConfig
from sloppatch.prepare import (
    RawHunkValidationError,
    RawPatchValidationError,
    raise_validate_raw_hunk,
    raise_validate_raw_patch,
)

from .helpers import make_change, make_raw_hunk


class TestRaiseValidateHunk:
    def test_valid_hunk(self) -> None:
        hunk = make_raw_hunk(
            1,
            3,
            3,
            3,
            changes=[
                make_change(RawAct.Context, "a"),
                make_change(RawAct.Delete, "b"),
                make_change(RawAct.Add, "c"),
                make_change(RawAct.Context, "d"),
            ],
        )  # before: context+delete=2, after: context+add=3
        raise_validate_raw_hunk(hunk, ParseConfig())  # no exception

    def test_before_length_mismatch(self) -> None:
        hunk = make_raw_hunk(
            1,
            99,
            3,
            3,
            changes=[
                make_change(RawAct.Context, "a"),
            ],
        )
        with pytest.raises(
            RawHunkValidationError, match="Original line count.+does not match"
        ):
            raise_validate_raw_hunk(hunk, ParseConfig())

    def test_after_length_mismatch(self) -> None:
        hunk = make_raw_hunk(
            1,
            1,
            3,
            99,
            changes=[
                make_change(RawAct.Context, "a"),
            ],
        )
        with pytest.raises(
            RawHunkValidationError, match="New line count.+does not match"
        ):
            raise_validate_raw_hunk(hunk, ParseConfig())

    def test_empty_hunk_raises(self) -> None:
        hunk = make_raw_hunk(1, 0, 2, 0, changes=[])
        with pytest.raises(RawHunkValidationError, match="Empty hunk"):
            raise_validate_raw_hunk(hunk, ParseConfig())

    def test_only_deletions_valid(self) -> None:
        # after count = 0 is allowed as long as before > 0.
        hunk = make_raw_hunk(
            1,
            2,
            3,
            0,
            changes=[
                make_change(RawAct.Delete, "x"),
                make_change(RawAct.Delete, "y"),
            ],
        )
        raise_validate_raw_hunk(hunk, ParseConfig())

    def test_only_additions_valid(self) -> None:
        hunk = make_raw_hunk(
            1,
            0,
            3,
            2,
            changes=[
                make_change(RawAct.Add, "x"),
                make_change(RawAct.Add, "y"),
            ],
        )
        raise_validate_raw_hunk(hunk, ParseConfig())


class TestRaiseValidatePatch:
    def test_non_overlapping(self) -> None:
        patch = [
            make_raw_hunk(1, 2, 1, 2),  # before [1,3), after [10,12)
            make_raw_hunk(5, 1, 5, 1),  # before [5,6), after [15,16)
        ]
        raise_validate_raw_patch(patch)  # no error

    def test_overlapping_before_begin(self) -> None:
        patch = [
            make_raw_hunk(1, 5, 10, 2),  # before [1,6)
            make_raw_hunk(3, 2, 20, 1),  # before [3,5)  -> 3 is inside [1,6)
        ]
        with pytest.raises(RawPatchValidationError, match="overlap"):
            raise_validate_raw_patch(patch)

    def test_overlapping_before_end(self) -> None:
        patch = [
            make_raw_hunk(5, 5, 10, 2),
            make_raw_hunk(1, 6, 20, 1),  # before [1,7) end=7, 5<=7<10 => overlap end
        ]
        with pytest.raises(RawPatchValidationError, match="overlap"):
            raise_validate_raw_patch(patch)

    def test_overlapping_engulfing(self) -> None:
        patch = [
            make_raw_hunk(5, 5, 5, 5),
            make_raw_hunk(2, 10, 2, 10),
        ]
        with pytest.raises(RawPatchValidationError, match="overlap"):
            raise_validate_raw_patch(patch)

    def test_overlapping_after_begin(self) -> None:
        patch = [
            make_raw_hunk(1, 2, 10, 5),  # after [10,15)
            make_raw_hunk(3, 1, 12, 2),  # after [12,14) -> 12 inside [10,15)
        ]
        with pytest.raises(RawPatchValidationError, match="overlap"):
            raise_validate_raw_patch(patch)

    def test_overlapping_after_end(self) -> None:
        patch = [
            make_raw_hunk(1, 2, 10, 5),  # after [10,15)
            make_raw_hunk(3, 1, 6, 6),  # after [6,12) end=12, 10<=12<15 => overlap end
        ]
        with pytest.raises(RawPatchValidationError, match="overlap"):
            raise_validate_raw_patch(patch)

    def test_empty_patch(self) -> None:
        raise_validate_raw_patch([])  # no error

    def test_valid_additions(self) -> None:
        # Hunk 1: orig 1..3 -> new 1..5 (delta +2)
        # Hunk 2: orig 5..5 -> new 7..9 (delta +2). Expected after.line: 5 + 2 = 7.
        h1 = make_raw_hunk(1, 3, 1, 5)
        h2 = make_raw_hunk(5, 1, 7, 3)
        raise_validate_raw_patch([h1, h2])

    def test_valid_deletions(self) -> None:
        # Hunk 1: orig 1..5 -> new 1..3 (delta -2)
        # Hunk 2: orig 7..7 -> new 5..6 (delta +1). Expected after.line: 7 - 2 = 5.
        h1 = make_raw_hunk(1, 5, 1, 3)
        h2 = make_raw_hunk(7, 1, 5, 2)
        raise_validate_raw_patch([h1, h2])

    def test_valid_zero_delta(self) -> None:
        # Hunk 1: orig 1..3 -> new 1..3 (delta 0, ignored in keys)
        # Hunk 2: orig 5..5 -> new 5..7 (delta +2). Expected after.line: 5 + 0 = 5.
        h1 = make_raw_hunk(1, 3, 1, 3)
        h2 = make_raw_hunk(5, 1, 5, 3)
        raise_validate_raw_patch([h1, h2])

    def test_invalid_after_line_too_small(self) -> None:
        # Hunk 1: orig 1..3 -> new 1..5 (delta +2)
        # Hunk 2: orig 5..1 -> new 6..2 (Invalid! Should be 7..2)
        h1 = make_raw_hunk(1, 3, 1, 5)
        h2 = make_raw_hunk(5, 1, 6, 2)
        with pytest.raises(
            RawPatchValidationError,
            match="Original start line and new start line validation failed",
        ):
            raise_validate_raw_patch([h1, h2])

    def test_invalid_after_line_too_large(self) -> None:
        # Hunk 1: orig 1..3 -> new 1..5 (delta +2)
        # Hunk 2: orig 5..1 -> new 8..2 (Invalid! Should be 7..2)
        h1 = make_raw_hunk(1, 3, 1, 5)
        h2 = make_raw_hunk(5, 1, 8, 2)
        with pytest.raises(
            RawPatchValidationError,
            match="Original start line and new start line validation failed",
        ):
            raise_validate_raw_patch([h1, h2])
