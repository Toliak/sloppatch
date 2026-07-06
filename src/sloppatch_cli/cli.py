import argparse

import dataclasses
import os
from pathlib import Path
import random
import string
import sys
from typing import Iterator, List, Optional, Tuple, get_args, get_type_hints

from sloppatch.config import PatchConfig
from sloppatch.error import SloppatchError
from sloppatch.file import file_to_lines_iter, full_pipeline, lines_iter_to_file
from sloppatch.patch.prepare_by_file import ValidatePatchLinesSimilarityError
from sloppatch.patch.raw_parse_data import RawAct

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
        type=str,
        choices=get_args(get_type_hints(PatchConfig)["ignore_case_rule"]),
        help="Ignore case while matching any line",
        required=False,
    )
    parser.add_argument(
        "--cfg-skip-context-lines",
        type=int,
        default=0,
        metavar="N",
        help="Maximum total number of lines that may be skipped while matching a single hunk (default: 0)",
        required=False,
    )

    # Parse arguments
    args = parser.parse_args(argv)

    # Create and return dataclass instance
    assert args.input is not None
    assert args.patch is not None

    patch_config = PatchConfig()
    if args.cfg_fuzz_context_lines:
        patch_config.fuzz_context_lines = args.cfg_fuzz_context_lines
    if args.cfg_trim_string:
        patch_config.trim_string = args.cfg_trim_string
    if args.cfg_ignore_whitespaces:
        patch_config.ignore_whitespaces = args.cfg_ignore_whitespaces
    if args.cfg_ignore_case:
        patch_config.ignore_case_rule = args.cfg_ignore_case
    if args.cfg_skip_context_lines:
        patch_config.skip_context_lines = args.cfg_skip_context_lines

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


def _act_to_char(act: RawAct) -> str:
    match act:
        case RawAct.Context:
            return '='
        case RawAct.Add:
            return '+'
        case RawAct.Delete:
            return '-'

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

    output_file_temp = args.input_file.parent / (
        args.input_file.name + "." + create_random_suffix()
    )
    try:
        output_iterator = full_pipeline(
            input_get_io=lambda: file_to_lines_iter(args.input_file),
            patch_io=file_to_lines_iter(args.patch_file),
            patch_config=patch_config,
        )
    except ValidatePatchLinesSimilarityError as e:
        print("Error while applying patch")
        print(str(e))
        max_change_idx = e.similar.max_change_idx
        print(f"Maximum similar place to the hunk on Line={e.similar.line}. Accepted changes ({max_change_idx}):")
        for c in e.hunk.changes[:max_change_idx]:
            print(_act_to_char(c.act), c.line.rstrip(), sep='')
        sys.exit(1)
    except SloppatchError as e:
        print("Error while applying patch")
        print(str(e))
        sys.exit(1)

    if args.output_file or args.inline:
        lines_iter_to_file(output_iterator, output_file_temp)
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
