#! /bin/bash

set -ueo pipefail
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

function case_01() {
    sloppatch -i "$SCRIPT_DIR"/case_01/input.txt -p "$SCRIPT_DIR"/case_01/patch.txt --cfg-fuzz-context-lines=4 --cfg-skip-context-lines=2
}

if case_01; then
    exit 1
else
    printf "== \x1b[32m%s\x1b[0m\n" "Case 01 ok"
fi

function case_02() {
    cp -f "$SCRIPT_DIR"/case_02/hello1.txt "$SCRIPT_DIR"/case_02/hello2.txt
    sloppatch -i "$SCRIPT_DIR"/case_02/ -p "$SCRIPT_DIR"/case_02/patch.diff -U --cfg-fuzz-context-lines=4 --cfg-skip-context-lines=2
}

if ! case_02; then
    exit 1
else
    printf "== \x1b[32m%s\x1b[0m\n" "Case 02 ok"
fi


function case_03() {
    cp -f "$SCRIPT_DIR"/case_03/input.txt "$SCRIPT_DIR"/case_03/output.txt
    sloppatch -L -i "$SCRIPT_DIR"/case_03/output.txt -p "$SCRIPT_DIR"/case_03/patch.txt

    local LINES
    LINES=$(cat tests/test_sloppatch_cli/case_03/output.txt | wc -l)
    if ! [ "$LINES" = 10 ]; then
        printf "== \x1b[31mWrong number of lines: %s\x1b[0m\n" "$LINES"
        return 1
    fi
}

if ! case_03; then
    exit 1
else
    printf "== \x1b[32m%s\x1b[0m\n" "Case 03 ok"
fi
