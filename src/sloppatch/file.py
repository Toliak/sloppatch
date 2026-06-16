from typing import Callable, Iterator, Optional

from .prepare import raw_patch_convert
from .apply import (
    PatchConfig,
    apply_patch,
    prepare_masked_patch,
    prepare_file_cache,
    prepare_patch_final,
)
from .parse import lines_to_raw_changes
from .data import ParseConfig


def full_pipeline(
    input_get_io: Callable[[], Iterator[str]],
    patch_io: Iterator[str],
    parse_config: Optional[ParseConfig] = None,
    patch_config: Optional[PatchConfig] = None,
) -> Iterator[str]:
    """Returns iterator of output lines (with endings)"""
    parse_config_ready = parse_config if parse_config is not None else ParseConfig()
    patch_config_ready = patch_config if patch_config is not None else PatchConfig()

    raw_patch = lines_to_raw_changes(patch_io, parse_config_ready)
    patch_conv = raw_patch_convert(raw_patch)
    masked_patch = prepare_masked_patch(patch_conv, patch_config_ready)
    file_cache = prepare_file_cache(
        masked_patch,
        patch_config_ready,
        input_get_io(),
    )
    prepared_patch = prepare_patch_final(masked_patch, file_cache, patch_config_ready)

    return apply_patch(prepared_patch, input_get_io())
