from dataclasses import dataclass
from enum import StrEnum


class OrderState(StrEnum):
    PENDING = 'pending'
    SEALED = 'sealed'


@dataclass(frozen=True, slots=True)
class ComparisonOrder:
    order_id: int
    a_revision_id: int
    b_revision_id: int
    state: OrderState
    receipt_id: int | None
