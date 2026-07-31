import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.calculation_factory import CalculationFactory
from app.database import Base


class Calculation(Base):
    """One arithmetic calculation owned by a user.

    The result is computed on demand through the factory rather than
    stored: a derived value in the row can drift from its operands,
    while a computed one cannot. The database enforces two invariants
    the application layer also checks — the type must be one of the
    four known operations, and a divide row can never hold a zero
    divisor — so bad data is rejected even if it bypasses Pydantic.
    """

    __tablename__ = "calculations"
    __table_args__ = (
        CheckConstraint(
            "type IN ('add', 'sub', 'multiply', 'divide')",
            name="ck_calculations_known_type",
        ),
        CheckConstraint(
            "NOT (type = 'divide' AND b = 0)",
            name="ck_calculations_nonzero_divisor",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    a: Mapped[float] = mapped_column(Float, nullable=False)
    b: Mapped[float] = mapped_column(Float, nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    @property
    def result(self) -> float:
        """Compute the result through the factory on every access."""
        return CalculationFactory.compute(self.type, self.a, self.b)

    def __repr__(self) -> str:
        return f"<Calculation {self.type} a={self.a} b={self.b}>"