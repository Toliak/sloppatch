from typing import Callable, Iterator, Optional

from sloppatch.prepare import raw_patch_convert

from .apply import PatchConfig, apply_patch, prepare_patch, prepare_patch_lines
from .parse import LineParseConfig, lines_to_raw_changes


def full_pipeline(
    input_get_io: Callable[[], Iterator[str]],
    patch_io: Iterator[str],
    parse_config: Optional[LineParseConfig] = None,
    patch_config: Optional[PatchConfig] = None,
) -> Iterator[str]:
    """Returns iterator of output lines (with endings)"""
    parse_config_ready = parse_config if parse_config is not None else LineParseConfig()
    patch_config_ready = patch_config if patch_config is not None else PatchConfig()

    raw_patch = lines_to_raw_changes( patch_io, parse_config_ready )
    patch_conv = raw_patch_convert(raw_patch)
    prepared_patch = prepare_patch(patch_conv, patch_config_ready)

    prepared_data = prepare_patch_lines(
        prepared_patch,
        patch_config_ready,
        input_get_io(),
    )
    return apply_patch(prepared_data, patch_config_ready, input_get_io())
