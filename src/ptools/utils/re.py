import re 

def test(
    query: str | None = None,
    regex: bool = False,
    
):
    """Test if a string matches a query, optionally using regex."""
    def matcher(s: str) -> bool:
        if regex:
            return re.search(query, s) is not None
        elif query is None:
            return True
        else:
            return query in s
    return matcher