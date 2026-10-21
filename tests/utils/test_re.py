"""Tests for ptools.utils.re.test (string matcher factory)."""
from ptools.utils.re import test as make_matcher, parse_regex_input


def test_none_query_matches_everything():
    match = make_matcher(query=None)
    assert match("anything") is True
    assert match("") is True


def test_substring_match():
    match = make_matcher(query="foo")
    assert match("food") is True
    assert match("bar") is False


def test_regex_match():
    match = make_matcher(query=r"^fo+$", regex=True)
    assert match("foo") is True
    assert match("foooo") is True
    assert match("bar") is False


def test_regex_no_match_does_not_raise():
    match = make_matcher(query=r"\d+", regex=True)
    assert match("abc") is False
    assert match("abc123") is True

def test_parse_regex_input():
    pattern, replacement = parse_regex_input("s/foo/bar/")
    assert pattern.match("foo")
    assert replacement == "bar"

    pattern, replacement = parse_regex_input("s/(\\w+)/bar \\1/")
    assert pattern.match("word")
    assert replacement == "bar \\1"

    pattern, replacement = parse_regex_input("/foo/i")
    assert pattern.match("FOO")
    assert replacement is None

    pattern, replacement = parse_regex_input("foo")
    assert pattern.match("foo")
    assert replacement is None