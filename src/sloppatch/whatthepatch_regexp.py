"""
See [https://github.com/cscorley/whatthepatch/blob/07b3e145ccd356cff202ff23d1694d6d4e9e0b2e/src/whatthepatch/patch.py]
"""

import re


# file_timestamp_str: str = "(.+?)(?:\t|:|  +)(.*)"

# diffcmd_header: re.Pattern = re.compile("^diff(?: .+)? (.+) (.+)$")
# unified_header_index: re.Pattern = re.compile("^Index: (.+)$")
# unified_header_old_line: re.Pattern = re.compile(r"^--- " + file_timestamp_str + "$")
# unified_header_new_line: re.Pattern = re.compile(r"^\+\+\+ " + file_timestamp_str + "$")

unified_hunk_start: re.Pattern = re.compile(r"^@@ -(\d+),(\d*) \+(\d+),(\d*) @@(.*)$")
unified_change: re.Pattern = re.compile("^([-+ ])(.*)$", re.DOTALL)
