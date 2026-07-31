"""Factory for arithmetic calculation strategies.

Each calculation type maps to one strategy class registered against the
CalculationType enum. The factory resolves a type string or enum member
to its strategy, so adding a new operation means writing one class with
one decorator — no caller changes anywhere in the data layer.
"""

import logging
from abc import ABC, abstractmethod
from enum import Enum

logger = logging.getLogger(__name__)


class CalculationType(str, Enum):
    """Canonical calculation type strings stored in the database."""

    ADD = "add"
    SUB = "sub"
    MULTIPLY = "multiply"
    DIVIDE = "divide"


class ArithmeticOperation(ABC):
    """Strategy interface: one concrete subclass per calculation type."""

    @abstractmethod
    def compute(self, a: float, b: float) -> float:
        """Return the result of applying this operation to a and b."""


_registry: dict[CalculationType, ArithmeticOperation] = {}


def _register(kind: CalculationType):
    """Class decorator binding a strategy to its CalculationType."""

    def bind(cls: type[ArithmeticOperation]) -> type[ArithmeticOperation]:
        _registry[kind] = cls()
        return cls

    return bind


@_register(CalculationType.ADD)
class Addition(ArithmeticOperation):
    def compute(self, a: float, b: float) -> float:
        return a + b


@_register(CalculationType.SUB)
class Subtraction(ArithmeticOperation):
    def compute(self, a: float, b: float) -> float:
        return a - b


@_register(CalculationType.MULTIPLY)
class Multiplication(ArithmeticOperation):
    def compute(self, a: float, b: float) -> float:
        return a * b


@_register(CalculationType.DIVIDE)
class Division(ArithmeticOperation):
    def compute(self, a: float, b: float) -> float:
        if b == 0:
            logger.error("division rejected: zero divisor (a=%s)", a)
            raise ValueError("divisor must be nonzero")
        return a / b


class CalculationFactory:
    """Resolves a calculation type to its registered strategy."""

    @staticmethod
    def operation_for(kind: "CalculationType | str") -> ArithmeticOperation:
        try:
            resolved = CalculationType(kind)
        except ValueError:
            raise ValueError(f"unsupported calculation type: {kind!r}") from None
        return _registry[resolved]

    @classmethod
    def compute(cls, kind: "CalculationType | str", a: float, b: float) -> float:
        return cls.operation_for(kind).compute(a, b)