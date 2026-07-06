from typing import Iterator


def spiral_range(start: int, range_begin: int, range_end: int) -> Iterator[int]:
    if not (range_begin <= start < range_end):
        return

    yield start

    begin_delta = abs(start - range_begin) + 1  # Included the begin nmb
    end_delta = abs(range_end - start)
    for delta in range(1, max(begin_delta, end_delta)):
        start_minus_delta = start - delta
        if range_begin <= start_minus_delta < range_end:
            yield start_minus_delta

        start_plus_delta = start + delta
        if range_begin <= start_plus_delta < range_end:
            yield start_plus_delta
