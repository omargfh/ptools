import re 

def test(
    query: str,
    regex: bool = False,
    
):
    """Test if a string matches a query, optionally using regex."""
    def matcher(s: str) -> bool:
        if regex:
            return re.search(query, s) is not None
        else:
            return query in s
    return matcher