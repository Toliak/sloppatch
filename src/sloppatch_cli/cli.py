import argparse

import dataclasses
import os
from pathlib import Path
import random
import string
import sys
from typing import Iterator, List, Optional, Tuple

from sloppatch.apply import (
    PatchConfig,
)
from sloppatch.file import full_pipeline

# SCRIPT_DIR = Path(__file__).parent
# PROJECT_DIR = SCRIPT_DIR


@dataclasses.dataclass
class Arguments:
    """Dataclass to store parsed arguments"""

    input_file: Path

    patch_file: Path

    output_file: Optional[Path]

    inline: bool
    """
    True if editing file in-place, False otherwise
    """


def parse_arguments(argv: List[str]) -> Tuple[Arguments, PatchConfig]:
    """Parse command line arguments and return them as a dataclass"""
    parser = argparse.ArgumentParser(
        description="Apply sloppatch to the file",
        # formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Add arguments
    parser.add_argument(
        "-i", "--input", type=Path, help="Input file path", required=True
    )
    parser.add_argument(
        "-p", "--patch", type=Path, help="Patch file path", required=True
    )
    parser.add_argument(
        "-o", "--output", type=Path, help="Output file path", required=False
    )
    parser.add_argument(
        "-L",
        "--inline",
        action="store_true",
        help="Edit file in-place (inline modification)",
        required=False,
    )

    # Patch configuration arguments
    parser.add_argument(
        "--cfg-fuzz-context-lines",
        type=int,
        default=0,
        metavar="N",
        help="Number of lines before/after to search for patch location (default: 0)",
        required=False,
    )

    parser.add_argument(
        "--cfg-trim-string",
        action="store_true",
        help="Trim strings while matching (auto-enabled by --ignore-whitespaces or --ignore-case)",
        required=False,
    )

    parser.add_argument(
        "--cfg-ignore-whitespaces",
        action="store_true",
        help="Completely ignore whitespaces while matching (auto-enables --trim-string)",
        required=False,
    )

    parser.add_argument(
        "--cfg-ignore-case",
        action="store_true",
        help="Ignore case while matching any line (auto-enables --trim-string)",
        required=False,
    )

    # Parse arguments
    args = parser.parse_args(argv)

    # Create and return dataclass instance
    assert args.input is not None
    assert args.patch is not None

    patch_config = PatchConfig(
        fuzz_context_lines=args.cfg_fuzz_context_lines,
        trim_string=args.cfg_trim_string,
        ignore_whitespaces=args.cfg_ignore_whitespaces,
        ignore_case_all=args.cfg_ignore_case,
    )
    args_data = Arguments(
        input_file=args.input,
        patch_file=args.patch,
        output_file=args.output,
        inline=args.inline or False,
    )
    return (args_data, patch_config)


def create_random_suffix(length: int = 6) -> str:
    # Combine all letters and numbers into one pool
    characters = string.ascii_letters + string.digits

    # Randomly choose characters and merge them into a single string
    return "".join(random.choices(characters, k=length))


def main():
    argv = sys.argv[1:]
    args, patch_config = parse_arguments(argv)

    print(f"Input file: {args.input_file}", file=sys.stderr)
    print(f"Patch file: {args.patch_file}", file=sys.stderr)
    print(f"Output file: {args.output_file}", file=sys.stderr)
    print(f"Inline mode: {args.inline}", file=sys.stderr)

    if not args.input_file.is_file():
        raise RuntimeError(f"Input '{args.input_file}' is not a file")
    if not args.patch_file.is_file():
        raise RuntimeError(f"Patch '{args.patch_file}' is not a file")
    if args.output_file and args.output_file.exists():
        raise RuntimeError(f"Output '{args.patch_file}' already exists")

    def _file_lines_iterator(path: Path) -> Iterator[str]:
        with open(path, "rt", encoding="UTF-8") as f:
            line = f.readline()
            while line:
                yield line
                line = f.readline()

    output_file_temp = args.input_file.parent / (
        args.input_file.name + "." + create_random_suffix()
    )
    output_iterator = full_pipeline(
        input_get_io=lambda: _file_lines_iterator(args.input_file),
        patch_io=_file_lines_iterator(args.patch_file),
        patch_config=patch_config,
    )

    if args.output_file or args.inline:
        with open(output_file_temp, "wt", encoding="UTF-8", newline="\n") as f_output:
            for line in output_iterator:
                f_output.write(line)

        if args.inline:
            os.rename(output_file_temp, args.input_file)
        else:
            assert args.output_file is not None
            os.rename(output_file_temp, args.output_file)

    else:
        for line in output_iterator:
            print(line, end="")


if __name__ == "__main__":
    main()
