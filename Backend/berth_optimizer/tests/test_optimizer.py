"""
Unit tests for the Berth Optimization Engine (v2).

Run from the project root (models/ folder):
    pytest berth_optimizer/tests/test_optimizer.py -v
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

# Ensure package is importable
sys.path.insert(0, str(Path(__file__).parents[2]))

from berth_optimizer.engine.optimizer import (
    AllocationResult,
    BerthOptimizationEngine,
    BerthScoringEngine,
    BerthSlot,
    ConflictDetector,
    ConstraintValidator,
    UtilizationTracker,
    VesselRequest,
    WaitingTimeCalculator,
)

# ─── Fixtures ─────────────────────────────────────────────────────────────────

NOW = datetime(2025, 7, 15, 10, 0, 0)


def make_vessel(
    vessel_id: str = "V001",
    loa_m: float = 200.0,
    draft_m: float = 10.0,
    eta_offset_h: float = 4.0,
    service_h: float = 6.0,
    congestion: float = 0.3,
) -> VesselRequest:
    eta = NOW + timedelta(hours=eta_offset_h)
    return VesselRequest(
        vessel_id=vessel_id,
        predicted_eta=eta.isoformat(),
        predicted_delay_minutes=0.0,
        loa_m=loa_m,
        draft_m=draft_m,
        port_congestion_index=congestion,
        estimated_service_time_hours=service_h,
    )


def make_berth(
    berth_id: str = "B1",
    max_len: float = 250.0,
    max_draft: float = 15.0,
    queue: int = 0,
    avail_offset_h: float = 0.0,
    crane_ratio: float = 0.9,
) -> BerthSlot:
    avail = NOW + timedelta(hours=avail_offset_h)
    return BerthSlot(
        berth_id=berth_id,
        berth_max_length=max_len,
        berth_queue_length=queue,
        berth_available_from=avail.isoformat(),
        crane_availability_ratio=crane_ratio,
        berth_max_draft=max_draft,
    )


def _make_alloc(berth_id, start_offset_h, end_offset_h) -> AllocationResult:
    start = NOW + timedelta(hours=start_offset_h)
    end   = NOW + timedelta(hours=end_offset_h)
    return AllocationResult(
        request_id=f"r_{berth_id}_{start_offset_h}",
        vessel_id="V_TEST",
        assigned_berth=berth_id,
        berthing_start_time=start.isoformat(),
        waiting_time_minutes=0.0,
        departure_time=end.isoformat(),
        berth_utilization=0.5,
        allocation_score=0.8,
        service_duration_hours=end_offset_h - start_offset_h,
        congestion_flag=False,
        conflict_flag=False,
    )


# ─── ConstraintValidator ─────────────────────────────────────────────────────

class TestConstraintValidator:

    def test_length_feasible_passes(self):
        assert ConstraintValidator.is_length_feasible(make_vessel(loa_m=200.0), make_berth(max_len=210.0))

    def test_length_feasible_fails(self):
        assert not ConstraintValidator.is_length_feasible(make_vessel(loa_m=206.0), make_berth(max_len=210.0))

    def test_draft_feasible_passes(self):
        assert ConstraintValidator.is_draft_feasible(make_vessel(draft_m=12.0), make_berth(max_draft=15.0))

    def test_draft_feasible_fails(self):
        assert not ConstraintValidator.is_draft_feasible(make_vessel(draft_m=16.0), make_berth(max_draft=15.0))

    def test_draft_feasible_exact_boundary(self):
        assert ConstraintValidator.is_draft_feasible(make_vessel(draft_m=15.0), make_berth(max_draft=15.0))

    def test_queue_acceptable(self):
        assert ConstraintValidator.is_queue_acceptable(make_berth(queue=5))

    def test_queue_rejected(self):
        assert not ConstraintValidator.is_queue_acceptable(make_berth(queue=6))

    def test_availability_valid(self):
        assert ConstraintValidator.is_available(make_berth(avail_offset_h=1.0))

    def test_availability_invalid(self):
        b = make_berth()
        b.berth_available_from = "not-a-date"
        assert not ConstraintValidator.is_available(b)

    def test_filter_all_pass(self):
        v = make_vessel(loa_m=200.0, draft_m=10.0)
        feasible, reasons = ConstraintValidator.filter_feasible_berths(v, [make_berth("B1"), make_berth("B2")])
        assert len(feasible) == 2 and reasons == []

    def test_filter_loa_rejection(self):
        feasible, reasons = ConstraintValidator.filter_feasible_berths(make_vessel(loa_m=260.0), [make_berth(max_len=250.0)])
        assert feasible == [] and "LOA" in reasons[0]

    def test_filter_draft_rejection(self):
        feasible, reasons = ConstraintValidator.filter_feasible_berths(make_vessel(draft_m=16.0), [make_berth(max_draft=15.0)])
        assert feasible == [] and "draft" in reasons[0].lower()

    def test_filter_queue_rejection(self):
        feasible, reasons = ConstraintValidator.filter_feasible_berths(make_vessel(), [make_berth(queue=7)])
        assert feasible == [] and "queue" in reasons[0].lower()

    def test_soft_fallback_within_loa_tolerance(self):
        v = make_vessel(loa_m=248.0)   # 3m over loa_limit=245; 1.2% < 5%
        candidates = ConstraintValidator.filter_soft_fallback(v, [make_berth(max_len=250.0)])
        assert len(candidates) == 1
        assert any("LOA" in v_str for _, violations in candidates for v_str in violations)

    def test_soft_fallback_exceeds_loa_tolerance(self):
        v = make_vessel(loa_m=260.0)   # 15m over; 6.1% > 5%
        assert ConstraintValidator.filter_soft_fallback(v, [make_berth(max_len=250.0)]) == []

    def test_soft_fallback_draft_within_tolerance(self):
        v = make_vessel(draft_m=15.4)  # 0.4m over <= 0.5
        assert len(ConstraintValidator.filter_soft_fallback(v, [make_berth(max_draft=15.0)])) == 1

    def test_soft_fallback_draft_exceeds_tolerance(self):
        v = make_vessel(draft_m=15.6)  # 0.6m over > 0.5
        assert ConstraintValidator.filter_soft_fallback(v, [make_berth(max_draft=15.0)]) == []


# ─── WaitingTimeCalculator ────────────────────────────────────────────────────

class TestWaitingTimeCalculator:

    def test_wait_when_eta_before_availability(self):
        v = make_vessel(eta_offset_h=4.0)
        b = make_berth(avail_offset_h=6.0, queue=0)
        wait, start, svc = WaitingTimeCalculator.compute_waiting_time(v, b)
        assert abs(wait - 120.0) < 0.1
        assert abs((start - (NOW + timedelta(hours=6))).total_seconds()) < 1

    def test_no_wait_when_eta_after_availability(self):
        v = make_vessel(eta_offset_h=6.0)
        b = make_berth(avail_offset_h=2.0, queue=0)
        wait, start, svc = WaitingTimeCalculator.compute_waiting_time(v, b)
        assert wait == 0.0

    def test_queue_adds_delay(self):
        v = make_vessel(eta_offset_h=0.0)
        b = make_berth(avail_offset_h=0.0, queue=4)   # Container: 4 * 20 = 80 min
        wait, start, svc = WaitingTimeCalculator.compute_waiting_time(v, b)
        assert abs(wait - 80.0) < 0.1

    def test_service_hours_returned(self):
        v = make_vessel(service_h=8.0)
        wait, start, svc = WaitingTimeCalculator.compute_waiting_time(v, make_berth())
        assert svc == 8.0

    def test_compute_from_start(self):
        v = make_vessel(eta_offset_h=4.0)
        new_start = NOW + timedelta(hours=5)
        wait, departure = WaitingTimeCalculator.compute_waiting_time_from_start(v, new_start, 6.0)
        assert abs(wait - 60.0) < 0.1
        assert abs((departure - (new_start + timedelta(hours=6))).total_seconds()) < 1


# ─── ConflictDetector ────────────────────────────────────────────────────────

class TestConflictDetector:

    def test_no_conflict_different_berth(self):
        existing = [_make_alloc("B1", 0, 6)]
        assert not ConflictDetector.detect_conflict("B2", NOW, NOW + timedelta(hours=6), existing)

    def test_no_conflict_no_overlap(self):
        existing = [_make_alloc("B1", 0, 6)]
        assert not ConflictDetector.detect_conflict("B1", NOW + timedelta(hours=7), NOW + timedelta(hours=13), existing)

    def test_conflict_overlap(self):
        existing = [_make_alloc("B1", 0, 6)]
        assert ConflictDetector.detect_conflict("B1", NOW + timedelta(hours=3), NOW + timedelta(hours=9), existing)

    def test_conflict_contained_within(self):
        existing = [_make_alloc("B1", 0, 10)]
        assert ConflictDetector.detect_conflict("B1", NOW + timedelta(hours=2), NOW + timedelta(hours=5), existing)

    def test_no_conflict_adjacent(self):
        existing = [_make_alloc("B1", 0, 6)]
        assert not ConflictDetector.detect_conflict("B1", NOW + timedelta(hours=6), NOW + timedelta(hours=12), existing)

    def test_last_departure_returns_max(self):
        allocs = [_make_alloc("B1", 0, 6), _make_alloc("B1", 7, 12)]
        last = ConflictDetector.last_departure("B1", allocs)
        assert abs((last - (NOW + timedelta(hours=12))).total_seconds()) < 1

    def test_last_departure_none_if_empty(self):
        assert ConflictDetector.last_departure("B1", []) is None


# ─── BerthOptimizationEngine ─────────────────────────────────────────────────

class TestBerthOptimizationEngine:

    def _e(self): return BerthOptimizationEngine()

    def test_normal_allocation(self):
        r = self._e().allocate(make_vessel("V1", loa_m=200.0, draft_m=10.0), [make_berth("B1")])
        assert r.assigned_berth == "B1" and r.conflict_flag is False

    def test_loa_too_large_fallback(self):
        r = self._e().allocate(make_vessel("V1", loa_m=300.0), [make_berth("B1", max_len=250.0)])
        assert r.conflict_flag is True
        assert any("fallback" in m.lower() or "HOLD" in m or "NO FEASIBLE" in m for m in r.alert_messages)

    def test_draft_rejection_fallback(self):
        r = self._e().allocate(make_vessel("V1", draft_m=20.0), [make_berth("B1", max_draft=15.0)])
        assert r.conflict_flag is True

    def test_no_berths_hold(self):
        r = self._e().allocate(make_vessel("V1"), [])
        assert r.assigned_berth == "HOLD"

    def test_conflict_resolution_reschedules(self):
        engine = self._e()
        b  = make_berth("B1", avail_offset_h=0.0)
        r1 = engine.allocate(make_vessel("V1", eta_offset_h=0.0, service_h=6.0), [b])
        assert r1.conflict_flag is False
        r2 = engine.allocate(make_vessel("V2", eta_offset_h=0.0, service_h=4.0), [b])
        import pandas as pd
        assert pd.to_datetime(r2.berthing_start_time) >= pd.to_datetime(r1.departure_time)

    def test_conflict_resolution_alert(self):
        engine = self._e()
        b = make_berth("B1", avail_offset_h=0.0)
        engine.allocate(make_vessel("V1", eta_offset_h=0.0, service_h=6.0), [b])
        r2 = engine.allocate(make_vessel("V2", eta_offset_h=0.0, service_h=4.0), [b])
        assert "resolved" in " ".join(r2.alert_messages).lower() or "rescheduled" in " ".join(r2.alert_messages).lower()

    def test_soft_fallback_used(self):
        r = self._e().allocate(make_vessel("V1", loa_m=248.0), [make_berth("B1", max_len=250.0)])
        assert r.assigned_berth == "B1" and r.conflict_flag is True

    def test_high_congestion_alert(self):
        r = self._e().allocate(make_vessel("V1", congestion=0.9), [make_berth("B1")])
        assert r.congestion_flag is True
        assert any("CONGESTION" in m for m in r.alert_messages)

    def test_weights_per_call_override(self):
        engine = self._e()
        r = engine.allocate(
            make_vessel("V1"),
            [make_berth("B1", crane_ratio=0.5), make_berth("B2", crane_ratio=0.9)],
            weights={"crane_availability": 0.8, "waiting_time": 0.1,
                     "queue_length": 0.05, "congestion": 0.025, "loa_fit": 0.025}
        )
        assert r.assigned_berth == "B2"

    def test_update_allocation_changes_berth(self):
        engine = self._e()
        r = engine.allocate(make_vessel("V1"), [make_berth("B1")])
        updated = engine.update_allocation(r.request_id, new_berth_id="B99")
        assert updated.assigned_berth == "B99"

    def test_update_allocation_not_found_raises(self):
        with pytest.raises(ValueError, match="No allocation found"):
            self._e().update_allocation("nonexistent_id")

    def test_get_port_kpis_empty(self):
        assert self._e().get_port_kpis()["total_allocations"] == 0

    def test_get_port_kpis_after_allocation(self):
        engine = self._e()
        engine.allocate(make_vessel("V1"), [make_berth("B1")])
        assert engine.get_port_kpis()["total_allocations"] == 1

    def test_clear_expired_returns_int(self):
        engine = self._e()
        engine.allocate(make_vessel("V1"), [make_berth("B1")])
        assert isinstance(engine.clear_expired_allocations(cutoff_hours=0), int)


# ─── allocate_batch ───────────────────────────────────────────────────────────

class TestAllocateBatch:

    def test_returns_same_count(self):
        engine = BerthOptimizationEngine()
        vessels = [make_vessel(f"V{i}", eta_offset_h=float(i)) for i in range(5)]
        results = engine.allocate_batch(vessels, [make_berth(f"B{i}") for i in range(3)])
        assert len(results) == len(vessels)

    def test_output_order_matches_input(self):
        engine = BerthOptimizationEngine()
        vessels = [make_vessel(f"V{i}", eta_offset_h=float(i)) for i in range(4)]
        results = engine.allocate_batch(vessels, [make_berth("B1")])
        for v, r in zip(vessels, results):
            assert r.vessel_id == v.vessel_id

    def test_greedy_resolves_conflicts(self):
        engine = BerthOptimizationEngine()
        v1 = make_vessel("V1", eta_offset_h=0.0, service_h=8.0)
        v2 = make_vessel("V2", eta_offset_h=0.0, service_h=4.0)
        b  = make_berth("B1", avail_offset_h=0.0)
        results = engine.allocate_batch([v1, v2], [b])
        import pandas as pd
        r1, r2 = results
        resolved_ok   = pd.to_datetime(r2.berthing_start_time) >= pd.to_datetime(r1.departure_time)
        diff_berth    = r1.assigned_berth != r2.assigned_berth
        conflict_kept = r2.conflict_flag is True
        assert resolved_ok or diff_berth or conflict_kept

    def test_batch_multiple_berths(self):
        engine = BerthOptimizationEngine()
        vessels = [make_vessel(f"V{i}", eta_offset_h=float(i * 2)) for i in range(4)]
        results = engine.allocate_batch(vessels, [make_berth("B1"), make_berth("B2")])
        assert all(r.assigned_berth in ("B1", "B2") for r in results)
