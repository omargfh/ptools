"""Shared enum types used across :mod:`ptools.utils`."""
from enum import Enum
from typing import List

__version__ = "0.1.0"


class LogicalOperators(Enum):
    """Boolean reducers used by requirement checks and similar predicates.

    Each member can :meth:`apply` itself to a list of booleans and reduce
    it to a single value, or :meth:`ensure` the result is true.
    """

    AND = 'and'
    OR = 'or'
    NONE = 'none'
    TRUE = 'true'
    FALSE = 'false'

    def apply(self, logical_results: List[bool]) -> bool:
        """Reduce ``logical_results`` according to this operator."""
        if self == LogicalOperators.AND:
            return all(logical_results)
        elif self == LogicalOperators.OR:
            return any(logical_results)
        elif self == LogicalOperators.NONE:
            return not any(logical_results)
        elif self == LogicalOperators.TRUE:
            return True
        elif self == LogicalOperators.FALSE:
            return False
        else:
            raise ValueError(f"Unknown logical operator: {self.value}")

    def ensure(self, logical_results: List[bool], message: str = ""):
        """Raise :class:`ValueError` if :meth:`apply` returns ``False``."""
        if not self.apply(logical_results):
            raise ValueError(f"Logical condition '{self.value}' not satisfied. {message}")