import argparse

import dataclasses
import os
from pathlib import Path
import random
import string
import sys
from typing import Dict, Iterator, List, Optional, Tuple, get_args, get_type_hints

from sloppatch.config import ParseConfig, PatchConfig
from sloppatch.error import SloppatchError
from sloppatch.file import file_to_lines_iter, full_pipeline, lines_iter_to_file
from sloppatch.patch.apply import apply_patch
from sloppatch.patch.convert import raw_patch_convert
from sloppatch.patch.prepare_by_file import ValidatePatchLinesSimilarityError, prepare_file_cache, prepare_patch_final
from sloppatch.patch.raw_parse_data import RawAct, RawHunk, RawPatch
from .unified import parse_unified_diff_to_raw_patches

# SCRIPT_DIR = Path(__file__).parent
# PROJECT_DIR = SCRIPT_DIR


@dataclasses.dataclass(frozen=True)
class Arguments:
    """Dataclass to store parsed arguments"""

    input_file: Path

    patch_file: Path

    output_file: Optional[Path]

    inline: bool
    """
    True if editing file in-place, False otherwise
    """

    unified: bool
    """
    Apply Unified patches using Sloppatch tool
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
        "-U",
        "--unified",
        action="store_true",
        help="Treat the patch as a Unified diff",
        required=False,
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
        unified=args.unified or False,
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


def apply_raw_patch_to_file(
    file_path: Path, 
    raw_patch: List[RawHunk], 
    parse_config: ParseConfig, 
    patch_config: PatchConfig,
    output_path: Optional[Path] = None,
    inline: bool = False
):
    """
    Apply a list of RawHunk objects to a single file using the internal pipeline.
    """
    patch_conv = raw_patch_convert(raw_patch, parse_config, patch_config)
    
    input_io = lambda: file_to_lines_iter(file_path)
                
    file_cache = prepare_file_cache(patch_conv, patch_config, input_io())
    prepared_patch = prepare_patch_final(patch_conv, file_cache, patch_config)
    output_iterator = apply_patch(prepared_patch, input_io())
    
    if output_path or inline:
        output_file_temp = file_path.parent / (file_path.name + ".tmp")
        lines_iter_to_file(output_iterator, output_file_temp)
                
        if inline:
            os.rename(output_file_temp, file_path)
        else:
            assert output_path is not None
            os.rename(output_file_temp, output_path)
    else:
        for line in output_iterator:
            print(line, end="")


def cli_apply_unified(args: Arguments, patch_config: PatchConfig) -> None:
    base_dir = args.input_file
    if not base_dir.is_dir():
        raise RuntimeError(f"Input (base dir in Unified mode) '{base_dir}' is not a directory")
    if args.output_file is not None:
        print("Output file will be ignored in Unified mode", file=sys.stderr)
    
    with open(args.patch_file, "rt", encoding="UTF-8") as f:
        patch_lines = f.readlines()
        
    file_to_raw_patch = parse_unified_diff_to_raw_patches(patch_lines)

    for file_rel_path, hunks in file_to_raw_patch.items():
        target_file = base_dir / file_rel_path
        if not target_file.is_file():
            print(f"Warning: Target file '{target_file}' not found. Skipping.", file=sys.stderr)
            continue

        out_file = None
        if args.output_file:
            # Treat output_file as a destination directory in unified mode
            out_file = args.output_file / file_rel_path
            out_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            apply_raw_patch_to_file(
                file_path=target_file, 
                raw_patch=hunks, 
                parse_config=ParseConfig(), 
                patch_config=patch_config,
                output_path=out_file,
                # Default to inline if no output directory is specified to avoid dumping mixed files to stdout
                inline=args.inline or (args.output_file is None)
            )
        except ValidatePatchLinesSimilarityError as e:
            print("Error while applying patch", file=sys.stderr)
            print(str(e), file=sys.stderr)
            max_change_idx = e.similar.max_change_idx
            print(f"Maximum similar place to the hunk on Line={e.similar.line}. Accepted changes ({max_change_idx}):", file=sys.stderr)
            for c in e.hunk.changes[:max_change_idx]:
                print(_act_to_char(c.act), c.line.rstrip(), sep='', file=sys.stderr)
            sys.exit(1)
        except SloppatchError as e:
            print("Error while applying patch", file=sys.stderr)
            print(str(e), file=sys.stderr)
            sys.exit(1)
        print(f"Applied patch to '{target_file}'", file=sys.stderr)

def cli_apply_sloppatch(args: Arguments, patch_config: PatchConfig) -> None:
    if not args.input_file.is_file():
        raise RuntimeError(f"Input '{args.input_file}' is not a file")
    if args.output_file and args.output_file.exists():
        raise RuntimeError(f"Output '{args.patch_file}' already exists. Specify '--inline' instead")

    try:
        output_iterator = full_pipeline(
            input_get_io=lambda: file_to_lines_iter(args.input_file),
            patch_io=file_to_lines_iter(args.patch_file),
            patch_config=patch_config,
        )
    except ValidatePatchLinesSimilarityError as e:
        print("Error while applying patch", file=sys.stderr)
        print(str(e), file=sys.stderr)
        max_change_idx = e.similar.max_change_idx
        print(f"Maximum similar place to the hunk on Line={e.similar.line}. Accepted changes ({max_change_idx}):", file=sys.stderr)
        for c in e.hunk.changes[:max_change_idx]:
            print(_act_to_char(c.act), c.line.rstrip(), sep='', file=sys.stderr)
        sys.exit(1)
    except SloppatchError as e:
        print("Error while applying patch", file=sys.stderr)
        print(str(e), file=sys.stderr)
        sys.exit(1)

    if args.output_file or args.inline:
        output_file_temp = args.input_file.parent / (
            args.input_file.name + "." + create_random_suffix()
        )
        lines_iter_to_file(output_iterator, output_file_temp)

        if args.inline:
            os.rename(output_file_temp, args.input_file)
        else:
            assert args.output_file is not None
            os.rename(output_file_temp, args.output_file)

    else:
        for line in output_iterator:
            print(line, end="")

def main() -> None:
    argv = sys.argv[1:]
    args, patch_config = parse_arguments(argv)

    print(f"Input file: {args.input_file}", file=sys.stderr)
    print(f"Patch file: {args.patch_file}", file=sys.stderr)
    print(f"Output file: {args.output_file}", file=sys.stderr)
    print(f"Inline mode: {args.inline}", file=sys.stderr)
    
    if not args.patch_file.is_file():
        raise RuntimeError(f"Patch '{args.patch_file}' is not a file")

    if args.unified:
        return cli_apply_unified(args, patch_config)
    else:
        return cli_apply_sloppatch(args, patch_config)


if __name__ == "__main__":
    main()
