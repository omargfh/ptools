"""Small regex / substring helpers for filtering strings and dicts."""
import re

__version__ = "0.1.0"


def test(
    query: str | None = None,
    regex: bool = False,

):
    """Test if a string matches a query, optionally using regex."""
    def matcher(s: str) -> bool:
        if regex:
            return re.search(str(query), s) is not None
        elif query is None:
            return True
        else:
            return query in s
    return matcher

def filter_dict_by_key(
    dict: dict,
    query: str | None = None,
    regex: bool = False,
) -> dict:
    """Filter a dictionary by keys matching a query, optionally using regex."""
    if query is None:
        return dict
    match = test(query, regex)
    return {k: v for k, v in dict.items() if match(k)}

def parse_regex_input(input: str) -> tuple[re.Pattern, str | None]:
    """Parse a CLI input string into a compiled regex pattern.

    Support formats:
    - Plain string: "abc" will match any string containing "abc"
    - Regex pattern: "\\.mp3$" will match any string ending with ".mp3"
    - Regex with delimiters: "/\\.mp3$/" will match any string ending with ".mp3"
    - Regex with flags: "/\\.mp3$/i" will match any string ending with ".mp3" case-insensitively
    - Regex replace: "s/\\.mp3$/\\.wav/" will replace ".mp3" with ".wav" in matching strings
    """
    input = input.strip()

    if input.startswith("s/"):
        # Handle regex replace format: s/pattern/replacement/
        parts = input[2:].split("/", 2)
        if len(parts) != 3:
            raise ValueError(f"Invalid regex replace format: {input}")
        pattern, replacement, _ = parts
        return re.compile(pattern), replacement

    elif input.startswith("/") and input.rfind("/") > 0:
        end = input.rfind("/")
        pattern = input[1:end]
        flags = input[end+1:]
        re_flags = 0
        if "i" in flags:
            re_flags |= re.IGNORECASE
        return re.compile(pattern, re_flags), None

    else:
        return re.compile(input), None
