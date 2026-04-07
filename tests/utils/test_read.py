"""Tests for ptools.utils.read.FromHumanized."""
import pytest

from ptools.utils.read import FromHumanized


@pytest.mark.parametrize(
    "text,expected",
    [
        ("10B", 10),
        ("1KB", 1024),
        ("1.5MB", int(1.5 * 1024**2)),
        ("2GB", 2 * 1024**3),
        ("0.5TB", int(0.5 * 1024**4)),
        ("1PB", 1024**5),
        ("  2 mb ", 2 * 1024**2),
        ("3.5 gb", int(3.5 * 1024**3)),
    ],
)
def test_from_humanized_size(text, expected):
    assert FromHumanized.from_humanized_size(text) == expected


@pytest.mark.parametrize("bad", ["100", "5XB", "abc", ""])
def test_from_humanized_size_invalid(bad):
    with pytest.raises(ValueError):
        FromHumanized.from_humanized_size(bad)
