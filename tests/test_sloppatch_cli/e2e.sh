#! /bin/bash

set -ueo pipefail
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

sloppatch -i "$SCRIPT_DIR"/input.txt -p "$SCRIPT_DIR"/patch.txt --cfg-fuzz-context-lines=4 --cfg-skip-context-lines=2
