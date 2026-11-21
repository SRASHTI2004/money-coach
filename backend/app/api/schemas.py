"""Validated request bodies (bounds on every number and list)."""
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from ..categorize import CATEGORIES
from ..config import MAX_CHAT_CHARS, MAX_PASTE_CHARS

MAX_MONEY = 1e10


class CategoryPatch(BaseModel):
    """Body for correcting a transaction category."""

    category: str = Field(min_length=1, max_length=40)


class PasteIn(BaseModel):
    """Pasted bank SMS or CSV text."""

    text: str = Field(min_length=1, max_length=MAX_PASTE_CHARS)
    kind: Literal["csv", "sms"] | None = None


class FixedCost(BaseModel):
    """A named fixed monthly cost."""

    name: str = Field(min_length=1, max_length=60)
    amount: float = Field(ge=0, le=MAX_MONEY)


class ProfileIn(BaseModel):
    """Partial profile update."""

    monthly_income: float | None = Field(None, ge=0, le=MAX_MONEY)
    fixed_costs: list[FixedCost] | None = Field(None, max_length=30)
    emergency_fund: float | None = Field(None, ge=0, le=MAX_MONEY)
    emergency_target_months: float | None = Field(None, ge=0, le=60)
    emergency_monthly: float | None = Field(None, ge=0, le=MAX_MONEY)
    budgets: dict[str, float] | None = None

    @field_validator("budgets")
    @classmethod
    def _budgets(cls, v: dict[str, float] | None) -> dict[str, float] | None:
        for k, amount in (v or {}).items():
            if k not in CATEGORIES or not 0 <= amount <= MAX_MONEY:
                raise ValueError(f"invalid budget for {k!r}")
        return v


class GoalIn(BaseModel):
    """A savings goal."""

    name: str = Field(min_length=1, max_length=80)
    target_amount: float = Field(gt=0, le=MAX_MONEY)
    saved: float = Field(0, ge=0, le=MAX_MONEY)
    target_date: date
    monthly_contrib: float = Field(0, ge=0, le=MAX_MONEY)


class Adjustment(BaseModel):
    """One what-if change: percent or monthly rupee amount on a category (or Income)."""

    category: str = Field(min_length=1, max_length=40)
    percent: float | None = Field(None, ge=-100, le=1000)
    amount: float | None = Field(None, ge=-1e8, le=1e8)


class SimIn(BaseModel):
    """What-if request."""

    adjustments: list[Adjustment] = Field(max_length=10)


class LifeEvent(BaseModel):
    """One life event for the month-by-month simulator."""

    type: Literal["salary_change", "job_loss", "rent_increase", "new_emi"]
    start: int = Field(1, ge=1, le=48)
    months: int | None = Field(None, ge=1, le=60)
    percent: float | None = Field(None, ge=-90, le=500)
    amount: float | None = Field(None, ge=0, le=1e7)
    cut_pct: float | None = Field(None, ge=0, le=100)


class LifeIn(BaseModel):
    """Life event scenario."""

    events: list[LifeEvent] = Field(max_length=8)

    def as_dicts(self) -> list[dict]:
        """Events as plain dicts without unset fields."""
        return [e.model_dump(exclude_none=True) for e in self.events]


class ChatIn(BaseModel):
    """A coach chat message."""

    message: str = Field(min_length=1, max_length=MAX_CHAT_CHARS)

    @field_validator("message")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("message is empty")
        return v


class UsedIn(BaseModel):
    """Mark a subscription as used on a date (default: latest data date)."""

    last_used: date | None = None
