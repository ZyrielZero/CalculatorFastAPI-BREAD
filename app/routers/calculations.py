"""Authenticated BREAD routes for the Calculation model.

Every route requires a valid bearer token and operates only on rows the
authenticated user owns. Lookups filter on (id, user_id) together, so a
calculation belonging to someone else is indistinguishable from one
that does not exist — both return the same 404, and the API never
leaks which ids are taken.

Edit is a PUT that replaces the three writable fields (a, b, type)
through the same CalculationCreate validation as Add, so an update can
never smuggle in a payload that creation would have refused.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_active_user
from app.database import get_db
from app.models.calculation import Calculation
from app.schemas.calculation import CalculationCreate, CalculationRead
from app.schemas.user import UserRead

router = APIRouter(prefix="/calculations", tags=["calculations"])


def _get_owned(db: Session, calculation_id: UUID, user_id: UUID) -> Calculation:
    """Fetch a calculation by id scoped to its owner, or raise 404."""
    row = db.scalar(
        select(Calculation).where(
            Calculation.id == calculation_id, Calculation.user_id == user_id
        )
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Calculation not found"
        )
    return row


@router.post("", response_model=CalculationRead, status_code=status.HTTP_201_CREATED)
def add_calculation(
    payload: CalculationCreate,
    db: Session = Depends(get_db),
    current_user: UserRead = Depends(get_current_active_user),
) -> CalculationRead:
    """Add: persist a calculation owned by the caller."""
    row = Calculation(
        a=payload.a, b=payload.b, type=payload.type.value, user_id=current_user.id
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return CalculationRead.model_validate(row)


@router.get("", response_model=list[CalculationRead])
def browse_calculations(
    db: Session = Depends(get_db),
    current_user: UserRead = Depends(get_current_active_user),
) -> list[CalculationRead]:
    """Browse: list the caller's calculations, oldest first."""
    rows = db.scalars(
        select(Calculation)
        .where(Calculation.user_id == current_user.id)
        .order_by(Calculation.created_at)
    ).all()
    return [CalculationRead.model_validate(row) for row in rows]


@router.get("/{calculation_id}", response_model=CalculationRead)
def read_calculation(
    calculation_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserRead = Depends(get_current_active_user),
) -> CalculationRead:
    """Read: fetch one calculation the caller owns."""
    return CalculationRead.model_validate(
        _get_owned(db, calculation_id, current_user.id)
    )


@router.put("/{calculation_id}", response_model=CalculationRead)
def edit_calculation(
    calculation_id: UUID,
    payload: CalculationCreate,
    db: Session = Depends(get_db),
    current_user: UserRead = Depends(get_current_active_user),
) -> CalculationRead:
    """Edit: replace operands and type, fully re-validated."""
    row = _get_owned(db, calculation_id, current_user.id)
    row.a = payload.a
    row.b = payload.b
    row.type = payload.type.value
    db.commit()
    db.refresh(row)
    return CalculationRead.model_validate(row)


@router.delete("/{calculation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_calculation(
    calculation_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserRead = Depends(get_current_active_user),
) -> None:
    """Delete: remove one calculation the caller owns."""
    row = _get_owned(db, calculation_id, current_user.id)
    db.delete(row)
    db.commit()