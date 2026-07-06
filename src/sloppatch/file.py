from pathlib import Path
from typing import TYPE_CHECKING, Callable, Iterator, Optional, TextIO

from sloppatch.utils.types import OpenTextModeReading, OpenTextModeWriting

from .patch.convert import raw_patch_convert
from .patch.prepare_by_file import (
    PatchConfig,
    prepare_file_cache,
    prepare_patch_final,
)
from .patch.apply import apply_patch
from .patch.raw_parse import lines_to_raw_changes
from .config import ParseConfig

def textio_to_lines_iter(text_io: TextIO) -> Iterator[str]:
    line = text_io.readline()
    while line:
        yield line
        line = text_io.readline()

def file_to_lines_iter(path: Path, mode: OpenTextModeReading = "rt", encoding: str = "UTF-8") -> Iterator[str]:
    with open(path, mode, encoding=encoding) as f:
        yield from textio_to_lines_iter(f)

def lines_iter_to_textio(iter: Iterator[str], text_io_out: TextIO) -> None:
    for line in iter:
        text_io_out.write(line)

def lines_iter_to_file(iter: Iterator[str], path: Path, mode: OpenTextModeWriting = "wt", encoding: str = "UTF-8", newline: str = "\n") -> None:
    with open(path, mode, encoding=encoding, newline=newline) as f:
        lines_iter_to_textio(iter, f)

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
    patch_conv = raw_patch_convert(raw_patch, parse_config_ready, patch_config_ready)
    file_cache = prepare_file_cache(
        patch_conv,
        patch_config_ready,
        input_get_io(),
    )
    prepared_patch = prepare_patch_final(patch_conv, file_cache, patch_config_ready)

    return apply_patch(prepared_patch, input_get_io())
