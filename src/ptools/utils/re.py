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