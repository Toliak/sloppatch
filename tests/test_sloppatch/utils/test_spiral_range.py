
from typing import List
from sloppatch.utils.spiral_range import spiral_range


class TestSpiralRange:
    def test_spiral_range_basic(self) -> None:
        result = list(spiral_range(5, 0, 10))
        expected: List[int] = [5, 4, 6, 3, 7, 2, 8, 1, 9, 0]
        assert result == expected

    def test_spiral_range_edge_case_start_at_beginning(self) -> None:
        result = list(spiral_range(0, 0, 5))
        expected: List[int] = [0, 1, 2, 3, 4]
        assert result == expected

    def test_spiral_range_edge_case_start_at_end(self) -> None:
        result = list(spiral_range(4, 0, 5))
        expected: List[int] = [4, 3, 2, 1, 0]
        assert result == expected

    def test_spiral_range_single_element(self) -> None:
        result = list(spiral_range(5, 5, 6))
        expected: List[int] = [5]
        assert result == expected

    def test_spiral_range_invalid_start(self) -> None:
        result: List[int] = list(spiral_range(10, 0, 5))  # start outside range
        expected: List[int] = []
        assert result == expected

    def test_spiral_range_negative_numbers(self) -> None:
        result = list(spiral_range(-1, -3, 3))
        expected: List[int] = [-1, -2, 0, -3, 1, 2]
        assert result == expected

    def test_spiral_range_large_range(self) -> None:
        result = list(spiral_range(2, 0, 6))
        expected: List[int] = [2, 1, 3, 0, 4, 5]
        assert result == expected

    def test_spiral_range_empty_range(self) -> None:
        result = list(spiral_range(0, 0, 0))
        expected: List[int] = []
        assert result == expected
