from typing import Literal, TypeAlias


LineIdx = int
"""
line index, begins with 0.
"""

LineNmb = int
"""
line number, begins with 1.
"""


OpenTextModeUpdating: TypeAlias = Literal[
    "r+",
    "+r",
    "rt+",
    "r+t",
    "+rt",
    "tr+",
    "t+r",
    "+tr",
    "w+",
    "+w",
    "wt+",
    "w+t",
    "+wt",
    "tw+",
    "t+w",
    "+tw",
    "a+",
    "+a",
    "at+",
    "a+t",
    "+at",
    "ta+",
    "t+a",
    "+ta",
    "x+",
    "+x",
    "xt+",
    "x+t",
    "+xt",
    "tx+",
    "t+x",
    "+tx",
]
"""
See [https://github.com/python/typeshed/blob/a7bcce8b6df32dd85dc31691cef30af61e7b1371/stdlib/_typeshed/__init__.pyi#L193-L229]
"""

OpenTextModeWriting: TypeAlias = Literal["w", "wt", "tw", "a", "at", "ta", "x", "xt", "tx"]
"""
See [https://github.com/python/typeshed/blob/a7bcce8b6df32dd85dc31691cef30af61e7b1371/stdlib/_typeshed/__init__.pyi#L193-L229]
"""

OpenTextModeReading: TypeAlias = Literal["r", "rt", "tr", "U", "rU", "Ur", "rtU", "rUt", "Urt", "trU", "tUr", "Utr"]
"""
See [https://github.com/python/typeshed/blob/a7bcce8b6df32dd85dc31691cef30af61e7b1371/stdlib/_typeshed/__init__.pyi#L193-L229]
"""
