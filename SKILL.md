# Sloppatch Skill

This document describes how to write **Sloppatch** patch files.

Sloppatch is a line-oriented patch format designed for LLMs. Unlike unified diff, it is intentionally simple, tolerant of nearby line movement (when configured), and does not require exact line counts.

## Basic structure

A patch consists of one or more **hunks**.

Each hunk starts with a header:

```text
# <START_LINE> # <OPTIONAL COMMENT>
```

Example:

```text
# 42 # Rename variable
```

`START_LINE` is **1-based**.

Everything after the second `#` is only a comment and has no semantic meaning.

## Line prefixes

Every line inside a hunk begins with exactly one control character.

| Prefix | Meaning |
|---------|----------|
| `=` | Context line (must exist before and after) |
| `-` | Delete this line |
| `+` | Insert this line |
| `/` | Previous added line has **no trailing newline** |

Example:

```text
# 15 # Replace function
=def foo():
-    return 1
+    return 2
```

## Hunk semantics

Think of the hunk as describing:

```
Before
↓

After
```

Context (`=`) exists in both versions.

Deleted lines (`-`) exist only before.

Added lines (`+`) exist only after.

Example:

Original

```python
a
b
c
```

Patch

```text
# 1 #
=a
-b
+x
=c
```

Result

```python
a
x
c
```

## Header

Format:

```text
# 123 # optional comment
```

Rules:

- line must start with `#`
- line number starts at **1**
- header is required before every hunk
- comments may be empty

Valid:

```text
# 1 #
# 25 # Update imports
```

Invalid:

```text
#1#
# abc #
```

## Context lines (`=`)

Context lines are used for locating the patch.

They:

- must match the original file
- remain unchanged after applying
- are the preferred way to uniquely identify where a patch belongs

Example:

```text
=class User:
=    def save(self):
```

## Delete lines (`-`)

Delete lines exist only in the original file.

Example:

```text
-old_value = 1
```


## Add lines (`+`)

Add lines exist only in the output.

Example:

```text
+new_value = 2
```

## End-of-file without newline

Normally every added line ends with a newline.

If the final added line should **NOT** end with a newline, write:

```text
+last line
/
```

The `/` always applies to the immediately preceding change line.

Example:

```text
# 100 #
+EOF
/
```

## Multiple hunks

Use multiple hunks for unrelated changes.

Example:

```text
# 10 # first
=foo
-old
+new

# 200 # second
=bar
-x
+y
```

## Choosing context

Always include enough surrounding context to uniquely identify the location.

Good:

```text
=def parse():
=value = load()
-old
+new
=return value
```

Bad:

```text
-old
+new
```

The latter is ambiguous.

### Add-only hunks

A hunk may contain only additions if the patch system allows it.

Example:

Insert before line 20:

```text
# 20 #
+print("debug")
```

Append to the end of the file:

If the file has N lines:

```text
# N+1 #
+new line
```

## Delete-only hunks

Perfectly valid.

Example:

```text
# 5 #
=foo
-remove me
=bar
```

#$ Replace

Replacement is simply delete followed by add.

```text
-old
+new
```

Never attempt to encode replacements in any other way.

#$ Preserve text exactly

Everything after the prefix is part of the line.

Do **not** normalize:

- indentation
- tabs
- trailing spaces
- capitalization

These are significant.

Example:

```text
-    value
+\tvalue
```

represents different text.

## Line numbering

`START_LINE` is an approximate location.

It refers to where the first **before** line is expected.

When fuzzy matching is enabled, the patch engine may relocate the hunk nearby.

Do not renumber later hunks to account for earlier edits.

Each hunk refers to the original file independently.

## Best practices for LLMs

### 1. Include context

Prefer:

```text
=if ready:
-old
+new
=return value
```

instead of:

```text
-old
+new
```

---

### 2. Keep hunks small

One logical edit per hunk whenever practical.

---

### 3. Avoid huge context

Usually 1–5 context lines are enough.

---

### 4. Preserve unchanged lines

Only use:

- `-` for removed lines
- `+` for inserted lines
- `=` for unchanged lines

---

### 5. Do not invent line numbers

Use the approximate location from the original file.

---

### 6. Comments are optional

These are equivalent:

```text
# 42 #
```

```text
# 42 # Rename helper
```

---

## Example

Original

```python
def add(a, b):
    return a+b
```

Patch

```text
# 1 # Format expression
=def add(a, b):
-    return a+b
+    return a + b
```

Result

```python
def add(a, b):
    return a + b
```


---

## Grammar

```
patch      ::= hunk+

hunk       ::= header change+

header     ::= "#" SP line_number SP "#" comment

change     ::= context
             | delete
             | add
             | nonewline

context    ::= "=" text
delete     ::= "-" text
add         ::= "+" text
nonewline  ::= "/"

line_number ::= positive_integer

comment    ::= arbitrary text
text       ::= arbitrary text (may be empty)
```


## Summary

```
# 15 # comment
=context
-delete
+insert
=context
```

Remember:

- `=` unchanged
- `-` remove
- `+` insert
- `/` previous added line has no newline
- one header per hunk
- line numbers are 1-based
- include enough context to uniquely locate the edit
- preserve whitespace exactly

