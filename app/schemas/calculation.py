from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.calculation_factory import CalculationType


class CalculationCreate(BaseModel):
    """Inbound payload: two operands and a calculation type.

    NaN and infinity are rejected at the field level, the type string
    is normalized so 'Add' and 'add' both resolve to the enum, and a
    zero divisor on a divide is refused before anything touches the
    factory or the database.
    """

    a: float = Field(allow_inf_nan=False)
    b: float = Field(allow_inf_nan=False)
    type: CalculationType

    @field_validator("type", mode="before")
    @classmethod
    def normalize_type(cls, value: object) -> object:
        # CalculationType subclasses str, so enum members lowercase to
        # their own value; anything non-string passes through untouched
        # and fails enum validation with Pydantic's own error.
        return value.lower() if isinstance(value, str) else value

    @model_validator(mode="after")
    def reject_zero_divisor(self) -> "CalculationCreate":
        if self.type is CalculationType.DIVIDE and self.b == 0:
            raise ValueError("divisor must be nonzero for a divide calculation")
        return self


class CalculationUpdate(BaseModel):
    """Partial update payload: any subset of the three writable fields.

    Nothing is validated in isolation here beyond field types, because a
    partial payload is not independently meaningful — whether b=0 is
    legal depends on the type already stored on the row. The route
    merges this onto the persisted values and re-validates the merged
    whole through CalculationCreate, so PATCH and POST answer to exactly
    one set of rules rather than two that can drift apart.
    """

    a: float | None = Field(default=None, allow_inf_nan=False)
    b: float | None = Field(default=None, allow_inf_nan=False)
    type: CalculationType | None = None

    @field_validator("type", mode="before")
    @classmethod
    def normalize_type(cls, value: object) -> object:
        # Same normalization as CalculationCreate: 'Divide' and 'divide'
        # resolve alike, and non-strings (including an explicit null)
        # pass through to be judged by the merge.
        return value.lower() if isinstance(value, str) else value

    @model_validator(mode="after")
    def reject_empty_payload(self) -> "CalculationUpdate":
        # An empty PATCH body is almost always a client bug; failing it
        # loudly beats a 200 that silently changed nothing.
        if not self.model_fields_set:
            raise ValueError("supply at least one of: a, b, type")
        return self


class CalculationRead(BaseModel):
    """Outbound representation. result is populated from the model's
    computed property, so the serialized value always reflects the
    stored operands."""

    id: UUID
    a: float
    b: float
    type: CalculationType
    result: float
    user_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)