"""
Vessel / Visit lifecycle transition guards.

Both statuses move through a strictly ordered sequence of operational
states. Once a status reaches a terminal state, it cannot move again.
Forward jumps (skipping an intermediate state, e.g. APPROACHING straight
to IN_PORT because no AIS ping was received while anchored) are allowed
since real-world updates don't always observe every intermediate state.
Backward jumps and any move out of a terminal state are not — those
indicate either a client bug or a stale/duplicate request, and silently
allowing them is how Dashboard/Port-Ops counts disagree with reality.
"""
from __future__ import annotations

from app.models.vessel import VesselStatus
from app.models.visit import VisitStatus


class InvalidTransitionError(ValueError):
    """Raised when a status transition violates the lifecycle order."""

    def __init__(self, old: str, new: str, entity: str = "entity"):
        self.old = old
        self.new = new
        self.entity = entity
        super().__init__(f"Cannot transition {entity} status from '{old}' to '{new}'")


# Ordered lifecycle — index position = progression order.
VESSEL_STATUS_ORDER: list[VesselStatus] = [
    VesselStatus.AT_SEA,
    VesselStatus.APPROACHING,
    VesselStatus.ANCHORED,
    VesselStatus.BERTHED,
    VesselStatus.DEPARTED,
]
VESSEL_TERMINAL_STATUSES = {VesselStatus.DEPARTED}

VISIT_STATUS_ORDER: list[VisitStatus] = [
    VisitStatus.SCHEDULED,
    VisitStatus.APPROACHING,
    VisitStatus.ANCHORED,
    VisitStatus.BERTHING,
    VisitStatus.IN_PORT,
    VisitStatus.DEPARTING,
    VisitStatus.COMPLETED,
]
# CANCELLED is reachable from any non-terminal visit status (a booking can
# be cancelled at any point before it completes) — it is not part of the
# linear order, just a side-terminal.
VISIT_TERMINAL_STATUSES = {VisitStatus.COMPLETED, VisitStatus.CANCELLED}


def _is_valid_transition(old, new, order: list, terminal: set) -> bool:
    if old == new:
        return True
    if old in terminal:
        return False
    if old not in order or new not in order:
        return False
    return order.index(new) >= order.index(old)


def is_valid_vessel_transition(old: VesselStatus, new: VesselStatus) -> bool:
    return _is_valid_transition(old, new, VESSEL_STATUS_ORDER, VESSEL_TERMINAL_STATUSES)


def is_valid_visit_transition(old: VisitStatus, new: VisitStatus) -> bool:
    if new == VisitStatus.CANCELLED:
        return old not in VISIT_TERMINAL_STATUSES
    return _is_valid_transition(old, new, VISIT_STATUS_ORDER, VISIT_TERMINAL_STATUSES)


def validate_vessel_transition(old: VesselStatus, new: VesselStatus) -> None:
    if not is_valid_vessel_transition(old, new):
        raise InvalidTransitionError(old.value, new.value, entity="vessel")


def validate_visit_transition(old: VisitStatus, new: VisitStatus) -> None:
    if not is_valid_visit_transition(old, new):
        raise InvalidTransitionError(old.value, new.value, entity="visit")
