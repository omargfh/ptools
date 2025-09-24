from enum import Enum
from typing import List

class LogicalOperators(Enum):
    AND = 'and'
    OR = 'or'
    NONE = 'none'
    TRUE = 'true'
    FALSE = 'false'
    
    def apply(self, logical_results: List[bool]) -> bool:
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
        if not self.apply(logical_results):
            raise ValueError(f"Logical condition '{self.value}' not satisfied. {message}")