"""Tests for the ptools proc filter expression language."""

import pytest

from ptools.lib.proc.query import QueryError, compile_query, substring_query


ROWS = {
    "chrome": {
        "pid": 100, "ppid": 1, "name": "Google Chrome", "comm": "Google Chrome",
        "cmd": "/Applications/Google Chrome.app/...", "user": "omar",
        "cpu": 55.0, "mem": 2 * 1024**3, "mem_pct": 6.3, "status": "running",
        "age": 7200.0, "label": "", "bundle": "Google Chrome",
        "ports": [], "conns": 12, "fds": 900, "kqueues": 3,
        "files": ["/Users/omar/Library/Caches/chrome.db"],
    },
    "node": {
        "pid": 200, "ppid": 150, "name": "node (vite.js)", "comm": "node",
        "cmd": "node vite.js --port 3000", "user": "omar",
        "cpu": 4.2, "mem": 300 * 1024**2, "mem_pct": 0.9, "status": "sleeping",
        "age": 90.0, "label": "Node.js", "bundle": "",
        "ports": [3000, 3001], "conns": 2, "fds": 120, "kqueues": 8,
        "files": ["/Users/omar/project/src/main.ts"],
    },
    "zombie": {
        "pid": 300, "ppid": 1, "name": "old-thing", "comm": "old-thing",
        "cmd": "", "user": "root",
        "cpu": 0.0, "mem": 0, "mem_pct": 0.0, "status": "zombie",
        "age": 900000.0, "label": "", "bundle": "",
        "ports": [], "conns": 0, "fds": 0, "kqueues": 0, "files": [],
    },
}


def matches(expression, **kwargs):
    query = compile_query(expression, **kwargs)
    return {name for name, row in ROWS.items() if query.match(row)}


def test_numeric_comparisons():
    assert matches("cpu>50") == {"chrome"}
    assert matches("cpu>=4.2") == {"chrome", "node"}
    assert matches("cpu<1") == {"zombie"}
    assert matches("pid=200") == {"node"}
    assert matches("pid!=200") == {"chrome", "zombie"}


def test_size_values_accept_humanized_literals():
    assert matches("mem>500MB") == {"chrome"}
    assert matches("mem>=300MB") == {"chrome", "node"}
    assert matches("mem>1048576") == {"chrome", "node"}  # plain bytes still work


def test_duration_values():
    assert matches("age>1h") == {"chrome", "zombie"}
    assert matches("age<5m") == {"node"}
    assert matches("age>120") == {"chrome", "zombie"}  # bare number = seconds


def test_string_operators():
    assert matches("user=omar") == {"chrome", "node"}
    assert matches("user=OMAR") == {"chrome", "node"}  # equality is case-insensitive
    assert matches("status!=zombie") == {"chrome", "node"}
    assert matches("name~chrome") == {"chrome"}
    assert matches("name~^node") == {"node"}  # regex
    assert matches("name!~node") == {"chrome", "zombie"}


def test_user_me_expands_to_current_user():
    assert matches("user=me", current_user="omar") == {"chrome", "node"}
    assert matches("user=me", current_user="nobody") == set()
    # Quoted 'me' means the literal user named me.
    assert matches("user='me'", current_user="omar") == set()


def test_port_membership():
    assert matches("port=3000") == {"node"}
    assert matches("port=9999") == set()
    assert matches("port>3000") == {"node"}
    assert matches("port!=3000") == {"chrome", "zombie"}  # no element equals 3000


def test_file_list_matching():
    assert matches("files~/Users/omar/project") == {"node"}
    assert matches("files~omar") == {"chrome", "node"}


def test_boolean_combinators_and_parens():
    assert matches("cpu>1 & user=omar") == {"chrome", "node"}
    assert matches("port=3000 | cpu>50") == {"chrome", "node"}
    assert matches("!status=zombie") == {"chrome", "node"}
    assert matches("(cpu>50 | fds>100) & user=omar") == {"chrome", "node"}
    assert matches("cpu>1 and user=omar") == {"chrome", "node"}
    assert matches("port=3000 or cpu>50") == {"chrome", "node"}
    assert matches("not status=zombie") == {"chrome", "node"}


def test_bare_word_is_substring_over_identity_fields():
    assert matches("chrome") == {"chrome"}
    assert matches("vite") == {"node"}       # display name
    assert matches("Node.js") == {"node"}    # label
    assert matches("root") == {"zombie"}     # user
    assert matches("nonexistent-thing") == set()


def test_quoted_values_with_spaces():
    assert matches('name="Google Chrome"') == {"chrome"}


def test_empty_query_matches_everything():
    assert matches("") == set(ROWS)
    assert matches(None) == set(ROWS)


def test_fields_used_and_required_joins():
    query = compile_query("port=3000 & fds>10 & cpu>1")
    assert query.fields_used == {"ports", "fds", "cpu"}
    assert query.required_joins() == {"ports", "watchers"}
    assert compile_query("cpu>1").required_joins() == set()


def test_aliases_resolve_to_canonical_fields():
    assert matches("rss>500MB") == {"chrome"}
    assert matches("mem%>5") == {"chrome"}
    assert compile_query("port=1").fields_used == {"ports"}


@pytest.mark.parametrize("expression", [
    "unknownfield=1",     # unknown field
    "cpu~50",             # regex op on numeric field
    "name>abc",           # ordering op on text field
    "cpu>",               # missing value
    "cpu>abc",            # non-numeric value
    "age>10x",            # unknown duration unit
    "(cpu>1",             # unbalanced paren
    "name~'unterminated", # unterminated quote
    "cpu>1 &",            # trailing operator
])
def test_invalid_expressions_raise(expression):
    with pytest.raises(QueryError):
        compile_query(expression)


def test_substring_fallback_never_raises():
    query = substring_query("cpu>>>((bogus")
    assert not query.match(ROWS["chrome"])
    assert substring_query("chrome").match(ROWS["chrome"])


def test_none_values_never_match_numeric_comparisons():
    row = dict(ROWS["chrome"], cpu=None)
    assert not compile_query("cpu>0").match(row)
    assert not compile_query("cpu<100").match(row)
