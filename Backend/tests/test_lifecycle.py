"""Unit tests for app.core.lifecycle — vessel/visit status transition guards.

Pure unit tests: no DB, no HTTP, no fixtures required.
"""
import pytest

from app.core.lifecycle import (
    InvalidTransitionError,
    is_valid_vessel_transition,
    is_valid_visit_transition,
    validate_vessel_transition,
    validate_visit_transition,
)
from app.models.vessel import VesselStatus
from app.models.visit import VisitStatus


class TestVesselTransitions:
    @pytest.mark.parametrize("old,new", [
        (VesselStatus.AT_SEA, VesselStatus.APPROACHING),
        (VesselStatus.APPROACHING, VesselStatus.ANCHORED),
        (VesselStatus.ANCHORED, VesselStatus.BERTHED),
        (VesselStatus.BERTHED, VesselStatus.DEPARTED),
        (VesselStatus.AT_SEA, VesselStatus.BERTHED),       # forward skip allowed
        (VesselStatus.APPROACHING, VesselStatus.APPROACHING),  # no-op allowed
    ])
    def test_valid_forward_transitions(self, old, new):
        assert is_valid_vessel_transition(old, new) is True
        validate_vessel_transition(old, new)  # must not raise

    @pytest.mark.parametrize("old,new", [
        (VesselStatus.DEPARTED, VesselStatus.AT_SEA),       # spec example
        (VesselStatus.BERTHED, VesselStatus.APPROACHING),   # backward
        (VesselStatus.ANCHORED, VesselStatus.AT_SEA),       # backward
        (VesselStatus.DEPARTED, VesselStatus.APPROACHING),  # out of terminal
    ])
    def test_invalid_transitions_blocked(self, old, new):
        assert is_valid_vessel_transition(old, new) is False
        with pytest.raises(InvalidTransitionError):
            validate_vessel_transition(old, new)


class TestVisitTransitions:
    @pytest.mark.parametrize("old,new", [
        (VisitStatus.SCHEDULED, VisitStatus.APPROACHING),
        (VisitStatus.APPROACHING, VisitStatus.ANCHORED),
        (VisitStatus.ANCHORED, VisitStatus.BERTHING),
        (VisitStatus.BERTHING, VisitStatus.IN_PORT),
        (VisitStatus.IN_PORT, VisitStatus.DEPARTING),
        (VisitStatus.DEPARTING, VisitStatus.COMPLETED),
        (VisitStatus.SCHEDULED, VisitStatus.IN_PORT),        # forward skip allowed
        (VisitStatus.APPROACHING, VisitStatus.APPROACHING),  # no-op allowed
    ])
    def test_valid_forward_transitions(self, old, new):
        assert is_valid_visit_transition(old, new) is True
        validate_visit_transition(old, new)  # must not raise

    @pytest.mark.parametrize("old,new", [
        (VisitStatus.COMPLETED, VisitStatus.APPROACHING),  # spec example
        (VisitStatus.IN_PORT, VisitStatus.SCHEDULED),       # backward (also spec's "AT_SEA" analogue)
        (VisitStatus.BERTHING, VisitStatus.ANCHORED),       # backward
        (VisitStatus.CANCELLED, VisitStatus.SCHEDULED),     # out of terminal
        (VisitStatus.COMPLETED, VisitStatus.CANCELLED),     # out of terminal
    ])
    def test_invalid_transitions_blocked(self, old, new):
        assert is_valid_visit_transition(old, new) is False
        with pytest.raises(InvalidTransitionError):
            validate_visit_transition(old, new)

    @pytest.mark.parametrize("old", [
        VisitStatus.SCHEDULED, VisitStatus.APPROACHING, VisitStatus.ANCHORED,
        VisitStatus.BERTHING, VisitStatus.IN_PORT, VisitStatus.DEPARTING,
    ])
    def test_cancel_allowed_from_any_non_terminal_status(self, old):
        assert is_valid_visit_transition(old, VisitStatus.CANCELLED) is True

    def test_cancel_blocked_from_completed(self):
        assert is_valid_visit_transition(VisitStatus.COMPLETED, VisitStatus.CANCELLED) is False
