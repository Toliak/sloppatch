from sloppatch.data import RawAct
import pytest
from sloppatch.data import ParseConfig
from sloppatch.prepare import (
    RawHunkValidationError,
    raise_validate_raw_hunk,
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

    def test_only_additions_rejected(self) -> None:
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

        with pytest.raises(RawHunkValidationError):
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
        raise_validate_raw_hunk(hunk, ParseConfig(hunk_add_only_rule="apply"))
