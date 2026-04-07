"""Tests for ptools.utils.enums.LogicalOperators."""
import pytest

from ptools.utils.enums import LogicalOperators


@pytest.mark.parametrize(
    "op,inputs,expected",
    [
        (LogicalOperators.AND, [True, True, True], True),
        (LogicalOperators.AND, [True, False], False),
        (LogicalOperators.AND, [], True),  # all([]) is True
        (LogicalOperators.OR, [False, False, True], True),
        (LogicalOperators.OR, [False, False], False),
        (LogicalOperators.OR, [], False),
        (LogicalOperators.NONE, [False, False], True),
        (LogicalOperators.NONE, [False, True], False),
        (LogicalOperators.TRUE, [False, False], True),
        (LogicalOperators.FALSE, [True, True], False),
    ],
)
def test_apply(op, inputs, expected):
    assert op.apply(inputs) is expected


def test_ensure_passes_silently_when_condition_holds():
    LogicalOperators.AND.ensure([True, True])


def test_ensure_raises_when_condition_fails():
    with pytest.raises(ValueError, match="not satisfied"):
        LogicalOperators.AND.ensure([True, False], "custom msg")
