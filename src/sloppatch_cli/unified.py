from pathlib import Path
import re
from typing import Dict, List

from sloppatch.patch.raw_parse_data import RawAct, RawChange, RawHunk, RawPatch

# See https://github.com/cscorley/whatthepatch/blob/07b3e145ccd356cff202ff23d1694d6d4e9e0b2e/src/whatthepatch/patch.py#L17-L27

file_timestamp_str = "(.+?)(?:\t|:|  +)(.*)"

unified_header_index = re.compile("^Index: (.+)$")
unified_header_old_line = re.compile(r"^--- " + file_timestamp_str + "$")
unified_header_new_line = re.compile(r"^\+\+\+ " + file_timestamp_str + "$")
unified_hunk_start = re.compile(r"^@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@(.*)$")
unified_change = re.compile("^([-+ ])(.*)$")

# ---

# WARN: by qwen, lmao didn't read
def parse_unified_diff_to_raw_patches(patch_lines: List[str]) -> Dict[Path, RawPatch]:
    """
    Parse a unified diff into a dictionary mapping file paths to lists of RawHunk objects.
    """
    patches: Dict[Path, List[RawHunk]] = {}
    
    current_file = None
    current_hunk = None
    
    i = 0
    while i < len(patch_lines):
        raw_line = patch_lines[i]
        line = raw_line.rstrip('\n').rstrip('\r')
        
        m_minus = unified_header_old_line.match(line)
        if m_minus and i + 1 < len(patch_lines):
            next_line = patch_lines[i+1].rstrip('\n').rstrip('\r')
            m_plus = unified_header_new_line.match(next_line)
            if m_plus:
                if current_hunk is not None and current_file is not None:
                    patches.setdefault(current_file, []).append(current_hunk)
                    current_hunk = None

                file_path = m_plus.group(1)
                if file_path == "/dev/null":
                    file_path = m_minus.group(1)
                current_file = Path(file_path)
                i += 2
                continue
                
        m_hunk = unified_hunk_start.match(line)
        if m_hunk and current_file is not None:
            if current_hunk is not None:
                patches.setdefault(current_file, []).append(current_hunk)
            
            start_line = int(m_hunk.group(1))
            comment = m_hunk.group(5).strip()
            current_hunk = RawHunk(start_line=start_line, comment=comment, changes=[])
            i += 1
            continue
            
        if current_hunk is not None:
            if line.startswith('+'):
                current_hunk.changes.append(RawChange(RawAct.Add, line[1:] + '\n'))
            elif line.startswith('-'):
                current_hunk.changes.append(RawChange(RawAct.Delete, line[1:] + '\n'))
            elif line.startswith(' '):
                current_hunk.changes.append(RawChange(RawAct.Context, line[1:] + '\n'))
            elif line.startswith('\\'):
                if current_hunk.changes:
                    last = current_hunk.changes[-1]
                    current_hunk.changes[-1] = RawChange(last.act, last.line, no_newline=True)
            elif line == "":
                # Ignore completely empty lines, they are usually just separators between hunks/files
                pass
                
        i += 1
        
    if current_hunk is not None and current_file is not None:
        patches.setdefault(current_file, []).append(current_hunk)
        
    return patches