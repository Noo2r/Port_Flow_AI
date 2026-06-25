"""
Berth Optimization Engine  (v2)
================================
Stage 2 of the Smart Port AI Pipeline.

Changelog vs v1:
    §1  Conflict resolution by rescheduling
    §2  Draft feasibility constraint
    §3  Dynamic / configurable scoring weights
    §4  Improved soft-constraint fallback allocation
    §5  Batch allocation method
    §6  Stochastic service-time distribution
    §7  update_allocation() for future API expansion
"""

from __future__ import annotations

import os
import random
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd

# ─── Data Structures ──────────────────────────────────────────────────────────

@dataclass
class VesselRequest:
    """
    Incoming vessel allocation request.
    Combines ETA model outputs (stage 1) with vessel + port features.
    """
    vessel_id: str
    request_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    # ETA model outputs
    predicted_eta: str = ""
    predicted_delay_minutes: float = 0.0

    # Vessel characteristics
    vessel_type: str = "Container"
    loa_m: float = 200.0
    draft_m: float = 10.0
    gross_tonnage: float = 50000.0
    vessel_age_years: float = 10.0
    speed_knots: float = 14.0
    distance_to_port_nm: float = 100.0

    # Port/berth context
    port_id: str = ""                       # Destination port (e.g. "PORT_A")
    port_congestion_index: float = 0.5
    traffic_density: str = "Medium"
    port_avg_delay_last_24h: float = 20.0

    # Time context
    timestamp: str = ""
    hour: int = 12
    day_of_week: int = 0
    is_weekend: bool = False
    is_night: bool = False

    # Service requirement (§6: range-based)
    estimated_service_time_hours: float = 6.0
    min_service_hours: Optional[float] = None
    max_service_hours: Optional[float] = None

    # Operational priority (§9): 0=normal, 1=commercial_priority, 2=emergency
    priority: int = 0

    # Weather context passed from ETA model (§10: weather-aware scoring)
    wave_height_m: float = 1.5

    def predicted_eta_dt(self) -> datetime:
        """Parse predicted_eta ISO string to datetime."""
        return pd.to_datetime(self.predicted_eta)

    def service_time_range(self) -> tuple[float, float]:
        """Return (min, max) service hours. Both equal estimated_service_time_hours if not set."""
        lo = self.min_service_hours if self.min_service_hours is not None else self.estimated_service_time_hours
        hi = self.max_service_hours if self.max_service_hours is not None else self.estimated_service_time_hours
        return lo, hi


@dataclass
class BerthSlot:
    """
    Represents a single berth with its current state and operational limits.
    """
    berth_id: str
    berth_max_length: float          # Maximum LOA the berth can accommodate (m)
    berth_queue_length: int          # Vessels currently queued
    berth_available_from: str        # ISO datetime when berth next becomes free
    crane_availability_ratio: float  # 0-1, fraction of cranes operational
    berth_max_draft: float = 15.0    # §2: Maximum vessel draft (m), default 15 m
    weather_shelter: float = 0.0    # §10: 0=fully exposed, 1=fully sheltered

    def available_from_dt(self) -> datetime:
        """Parse berth_available_from ISO string to datetime."""
        return pd.to_datetime(self.berth_available_from)


@dataclass
class AllocationResult:
    """
    Output of the berth optimization engine.
    Consumed downstream by the Congestion Forecast Model and dashboard.
    External API contract is unchanged from v1.
    """
    request_id: str
    vessel_id: str

    assigned_berth: str
    berthing_start_time: str
    waiting_time_minutes: float
    departure_time: str

    berth_utilization: float
    allocation_score: float

    service_duration_hours: float
    congestion_flag: bool
    conflict_flag: bool
    alert_messages: list[str] = field(default_factory=list)

    allocated_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )

    def to_dict(self) -> dict:
        """Serialise to plain dict."""
        return asdict(self)

    def to_api_response(self) -> dict:
        """Canonical API response format – contract unchanged from v1."""
        return {
            "assigned_berth": self.assigned_berth,
            "berthing_start_time": self.berthing_start_time,
            "waiting_time_minutes": round(self.waiting_time_minutes, 1),
            "departure_time": self.departure_time,
            "berth_utilization": round(self.berth_utilization, 3),
            "conflict_flag": self.conflict_flag,
            "congestion_flag": self.congestion_flag,
            "alert_messages": self.alert_messages,
            "request_id": self.request_id,
        }


# ─── Constraint Validation ────────────────────────────────────────────────────

class ConstraintValidator:
    """
    Rule-based filter: eliminates berths that violate hard operational constraints.

    Hard constraints (all must pass to be feasible):
        - Berth availability window parseable
        - Vessel LOA <= berth_max_length - LOA_SAFETY_BUFFER_M
        - Vessel draft <= berth_max_draft                    (§2)
        - Queue length <= MAX_QUEUE_THRESHOLD
        - Berth port_id matches vessel destination port_id   (§8)
    """

    LOA_SAFETY_BUFFER_M: float = 5.0
    MAX_QUEUE_THRESHOLD: int = 5

    # §4 soft-constraint tolerances for fallback
    LOA_SOFT_TOLERANCE_PCT: float = 0.05   # accept LOA overshoot <= 5 %
    DRAFT_SOFT_TOLERANCE_M: float = 0.5    # accept draft overshoot <= 0.5 m

    @staticmethod
    def is_length_feasible(vessel: VesselRequest, berth: BerthSlot) -> bool:
        """Vessel LOA must fit within the berth with a safety buffer."""
        return vessel.loa_m <= (berth.berth_max_length - ConstraintValidator.LOA_SAFETY_BUFFER_M)

    @staticmethod
    def is_draft_feasible(vessel: VesselRequest, berth: BerthSlot) -> bool:
        """§2: Vessel draft must not exceed the berth maximum draft."""
        return vessel.draft_m <= berth.berth_max_draft

    @staticmethod
    def is_available(berth: BerthSlot) -> bool:
        """Berth must have a parseable availability datetime."""
        try:
            berth.available_from_dt()
            return True
        except Exception:
            return False

    @staticmethod
    def is_queue_acceptable(berth: BerthSlot) -> bool:
        """Reject berths whose queue length exceeds the hard threshold."""
        return berth.berth_queue_length <= ConstraintValidator.MAX_QUEUE_THRESHOLD

    @classmethod
    def filter_feasible_berths(
        cls, vessel: "VesselRequest", berths: list[BerthSlot]
    ) -> tuple[list[BerthSlot], list[str]]:
        """
        Apply all hard constraints.

        Returns
        -------
        (feasible_berths, rejection_reasons)
            feasible_berths  : Berths that pass every hard constraint.
            rejection_reasons: Human-readable explanation for each rejection.
        """
        feasible: list[BerthSlot] = []
        reasons: list[str] = []

        for berth in berths:
            if not cls.is_available(berth):
                reasons.append(f"Berth {berth.berth_id}: invalid availability window")
                continue
            # §8: Port constraint — berth must belong to the vessel's destination port.
            # berth_id format is "PORT_X_Bnn", so we check the prefix against vessel.port_id.
            if vessel.port_id:
                expected_prefix = vessel.port_id.upper() + "_"
                if not berth.berth_id.upper().startswith(expected_prefix):
                    reasons.append(
                        f"Berth {berth.berth_id}: not in requested port {vessel.port_id}"
                    )
                    continue
            if not cls.is_length_feasible(vessel, berth):
                reasons.append(
                    f"Berth {berth.berth_id}: vessel LOA {vessel.loa_m}m exceeds "
                    f"capacity {berth.berth_max_length}m (buffer {cls.LOA_SAFETY_BUFFER_M}m)"
                )
                continue
            if not cls.is_draft_feasible(vessel, berth):
                reasons.append(
                    f"Berth {berth.berth_id}: vessel draft {vessel.draft_m}m exceeds "
                    f"berth max draft {berth.berth_max_draft}m"
                )
                continue
            # §9: Emergency vessels bypass the queue threshold — they must get a berth.
            if not cls.is_queue_acceptable(berth) and getattr(vessel, "priority", 0) < 2:
                reasons.append(
                    f"Berth {berth.berth_id}: queue {berth.berth_queue_length} "
                    f"> threshold {cls.MAX_QUEUE_THRESHOLD}"
                )
                continue
            feasible.append(berth)

        return feasible, reasons

    @classmethod
    def filter_soft_fallback(
        cls, vessel: VesselRequest, berths: list[BerthSlot]
    ) -> list[tuple[BerthSlot, list[str]]]:
        """
        §4: Return berths that fail hard constraints but pass within soft tolerances.

        Soft tolerances applied:
            - LOA overshoot <= LOA_SOFT_TOLERANCE_PCT  (5 %)
            - Draft overshoot <= DRAFT_SOFT_TOLERANCE_M (0.5 m)
            - Queue must still be acceptable (hard limit)
            - Availability window must be valid (hard limit)

        Returns
        -------
        List of (berth, violation_descriptions) sorted by nothing (caller sorts).
        """
        candidates: list[tuple[BerthSlot, list[str]]] = []
        for berth in berths:
            if not cls.is_available(berth):
                continue
            if not cls.is_queue_acceptable(berth):
                continue

            violations: list[str] = []

            loa_limit = berth.berth_max_length - cls.LOA_SAFETY_BUFFER_M
            loa_over  = vessel.loa_m - loa_limit
            if loa_over > 0:
                if loa_over / max(loa_limit, 1.0) > cls.LOA_SOFT_TOLERANCE_PCT:
                    continue
                violations.append(f"LOA overshoot {loa_over:.1f}m")

            draft_over = vessel.draft_m - berth.berth_max_draft
            if draft_over > 0:
                if draft_over > cls.DRAFT_SOFT_TOLERANCE_M:
                    continue
                violations.append(f"draft overshoot {draft_over:.2f}m")

            candidates.append((berth, violations))

        return candidates


# ─── Waiting Time Calculator ──────────────────────────────────────────────────

class WaitingTimeCalculator:
    """
    Computes waiting time and service duration for a vessel-berth pair.

    §6: Supports deterministic (default) and stochastic service-time sampling.
    """

    # §11: Vessel-type-aware queue delay (minutes per queued vessel ahead).
    # Tankers need more time for safety checks; RoRo vessels are quick to move.
    _QUEUE_DELAY_BY_TYPE: dict[str, float] = {
        "Container":    20.0,
        "Tanker":       30.0,
        "Bulk Carrier": 25.0,
        "RoRo":         15.0,
        "LNG Carrier":  35.0,
        "VLCC":         35.0,
        "General Cargo":20.0,
        "Car Carrier":  15.0,
        "Cruise":       20.0,
        "Feeder":       15.0,
    }
    _DEFAULT_QUEUE_DELAY: float = 20.0

    @classmethod
    def _queue_delay_minutes(cls, vessel: "VesselRequest") -> float:
        return cls._QUEUE_DELAY_BY_TYPE.get(vessel.vessel_type, cls._DEFAULT_QUEUE_DELAY)

    # §6: set True to sample service duration from Uniform(min, max)
    USE_RANDOM_SERVICE_TIME: bool = False

    @classmethod
    def _sample_service_hours(cls, vessel: VesselRequest) -> float:
        """
        §6: Sample service duration.

        If USE_RANDOM_SERVICE_TIME is True and the vessel specifies a range,
        draws from Uniform(min_service_hours, max_service_hours).
        Otherwise returns estimated_service_time_hours.
        """
        if cls.USE_RANDOM_SERVICE_TIME:
            lo, hi = vessel.service_time_range()
            if hi > lo:
                return random.uniform(lo, hi)
        return vessel.estimated_service_time_hours

    @classmethod
    def compute_waiting_time(
        cls, vessel: VesselRequest, berth: BerthSlot
    ) -> tuple[float, datetime, float]:
        """
        Compute waiting time and berthing schedule for a vessel-berth pair.

        Berthing start = max(predicted_eta, berth_available_from) + queue delay.
        Waiting time   = berthing_start - predicted_eta  (clamped >= 0).

        Returns
        -------
        (waiting_time_minutes, berthing_start_datetime, service_hours)
        """
        eta_dt    = vessel.predicted_eta_dt()
        avail_dt  = berth.available_from_dt()

        earliest_start = max(eta_dt, avail_dt)
        queue_delay    = timedelta(
            minutes=berth.berth_queue_length * cls._queue_delay_minutes(vessel)
        )
        berthing_start = earliest_start + queue_delay

        waiting_minutes = max(0.0, (berthing_start - eta_dt).total_seconds() / 60)
        service_hours   = cls._sample_service_hours(vessel)
        return waiting_minutes, berthing_start, service_hours

    @classmethod
    def compute_waiting_time_from_start(
        cls,
        vessel: VesselRequest,
        new_start: datetime,
        service_hours: float,
    ) -> tuple[float, datetime]:
        """
        §1: Compute waiting time and departure when the start is already determined
        (used during conflict rescheduling).

        Returns
        -------
        (waiting_time_minutes, departure_datetime)
        """
        eta_dt          = vessel.predicted_eta_dt()
        waiting_minutes = max(0.0, (new_start - eta_dt).total_seconds() / 60)
        departure       = new_start + timedelta(hours=service_hours)
        return waiting_minutes, departure


# ─── Berth Scoring Engine ─────────────────────────────────────────────────────

class BerthScoringEngine:
    """
    Multi-factor scoring model for ranking candidate berths (0-1 scale).

    Default weights (§3 – all runtime-configurable):
        waiting_time       0.35  lower wait  -> higher score
        queue_length       0.25  shorter queue -> higher score
        crane_availability 0.20  more cranes -> higher score
        congestion         0.10  less congestion -> higher score
        loa_fit            0.10  tighter fit (target ~90 % utilisation) -> higher score
    """

    DEFAULT_WEIGHTS: dict[str, float] = {
        "waiting_time":      0.33,
        "queue_length":      0.23,
        "crane_availability":0.19,
        "congestion":        0.10,
        "loa_fit":           0.10,
        "weather_shelter":   0.05,   # §10: bonus for sheltered berths in bad weather
    }
    WEIGHTS: dict[str, float] = DEFAULT_WEIGHTS.copy()

    MAX_WAIT_MINUTES: float = 360.0
    MAX_QUEUE: float = 5.0

    @classmethod
    def set_weights(cls, new_weights: dict[str, float]) -> None:
        """
        §3: Update class-level scoring weights for all future calls.

        Only keys present in new_weights are updated; others retain their value.
        Weights are auto-normalised so they always sum to 1.0.
        """
        cls.WEIGHTS.update(new_weights)
        total = sum(cls.WEIGHTS.values())
        if total > 0:
            cls.WEIGHTS = {k: v / total for k, v in cls.WEIGHTS.items()}

    @classmethod
    def score_berth(
        cls,
        vessel: VesselRequest,
        berth: BerthSlot,
        waiting_minutes: float,
        weights: Optional[dict[str, float]] = None,
    ) -> float:
        """
        Compute a 0-1 allocation score for a vessel-berth pair.

        Parameters
        ----------
        vessel          : VesselRequest
        berth           : BerthSlot
        waiting_minutes : Pre-computed waiting time (minutes)
        weights         : §3 Per-call override; falls back to cls.WEIGHTS.
        """
        w = weights if weights is not None else cls.WEIGHTS

        wait_score       = 1.0 - min(waiting_minutes / cls.MAX_WAIT_MINUTES, 1.0)
        queue_score      = 1.0 - min(berth.berth_queue_length / cls.MAX_QUEUE, 1.0)
        crane_score      = berth.crane_availability_ratio
        congestion_score = 1.0 - min(vessel.port_congestion_index, 1.0)
        loa_util         = vessel.loa_m / max(berth.berth_max_length, 1.0)
        loa_score        = max(0.0, 1.0 - abs(loa_util - 0.90))

        # §10: Weather-shelter score — only meaningful when waves are significant.
        # At calm seas (wave < 1 m) shelter confers no advantage; at wave ≥ 5 m
        # a fully sheltered berth scores 1.0 while an exposed berth scores 0.0.
        wave_factor      = min(vessel.wave_height_m / 5.0, 1.0)
        shelter_score    = berth.weather_shelter * wave_factor + (1.0 - wave_factor)

        score = (
            w.get("waiting_time",       0.33) * wait_score
            + w.get("queue_length",     0.23) * queue_score
            + w.get("crane_availability",0.19) * crane_score
            + w.get("congestion",       0.10) * congestion_score
            + w.get("loa_fit",          0.10) * loa_score
            + w.get("weather_shelter",  0.05) * shelter_score
        )
        return round(float(np.clip(score, 0.0, 1.0)), 4)


# ─── Conflict Detector ────────────────────────────────────────────────────────

class ConflictDetector:
    """Detects and assists in resolving scheduling conflicts."""

    @staticmethod
    def detect_conflict(
        berth_id: str,
        berthing_start: datetime,
        departure: datetime,
        active_allocations: list[AllocationResult],
    ) -> bool:
        """
        Return True if [berthing_start, departure) overlaps any active
        allocation at the same berth.
        """
        for alloc in active_allocations:
            if alloc.assigned_berth != berth_id:
                continue
            ex_start = pd.to_datetime(alloc.berthing_start_time)
            ex_end   = pd.to_datetime(alloc.departure_time)
            if berthing_start < ex_end and departure > ex_start:
                return True
        return False

    @staticmethod
    def last_departure(
        berth_id: str,
        active_allocations: list[AllocationResult],
    ) -> Optional[datetime]:
        """
        Return the latest departure time of all active allocations at berth_id,
        or None if there are none.
        """
        departures = [
            pd.to_datetime(a.departure_time)
            for a in active_allocations
            if a.assigned_berth == berth_id
        ]
        return max(departures) if departures else None


# ─── Utilization Tracker ──────────────────────────────────────────────────────

class UtilizationTracker:
    """Tracks berth occupancy over a rolling 48-hour window (±24 h from now)."""

    HALF_WINDOW_HOURS: int = 24   # total window = HALF_WINDOW_HOURS * 2 = 48 h

    @staticmethod
    def compute_utilization(
        berth_id: str,
        active_allocations: list[AllocationResult],
        reference_time: Optional[datetime] = None,
    ) -> float:
        """
        Fraction of the 48-hour window centred on reference_time during which
        the berth is occupied.  Returns 0.0 when no matching allocations exist.
        """
        if reference_time is None:
            reference_time = datetime.utcnow()

        window_start   = reference_time - timedelta(hours=UtilizationTracker.HALF_WINDOW_HOURS)
        window_end     = reference_time + timedelta(hours=UtilizationTracker.HALF_WINDOW_HOURS)
        window_minutes = UtilizationTracker.HALF_WINDOW_HOURS * 2 * 60

        occupied = 0.0
        for alloc in active_allocations:
            if alloc.assigned_berth != berth_id:
                continue
            s = max(pd.to_datetime(alloc.berthing_start_time), window_start)
            e = min(pd.to_datetime(alloc.departure_time),       window_end)
            if e > s:
                occupied += (e - s).total_seconds() / 60

        return round(min(occupied / window_minutes, 1.0), 4)


# ─── Main Optimization Engine ─────────────────────────────────────────────────

class BerthOptimizationEngine:
    """
    Production berth allocation engine (v2).

    Allocation workflow per vessel:
        1. Filter berths via hard constraints (LOA, draft, queue, availability)
        2. Compute waiting times + scores for every feasible berth
        3. Sort candidates by score (descending)
        4. For each candidate best-first: attempt §1 conflict resolution
        5. Accept the first candidate whose adjusted wait <= MAX_WAIT_FOR_CONFLICT_RESOLUTION
        6. If all fail: keep best-scoring berth with conflict_flag = True
        7. Compute utilization and emit operational alerts
    """

    CONGESTION_ALERT_THRESHOLD: float = 0.75
    HIGH_WAIT_ALERT_MINUTES: float = 120.0
    MAX_WAIT_FOR_CONFLICT_RESOLUTION: float = 360.0   # §1

    def __init__(self) -> None:
        self._active_allocations: list[AllocationResult] = []
        self._validator   = ConstraintValidator()
        self._wait_calc   = WaitingTimeCalculator()
        self._scorer      = BerthScoringEngine()
        self._conflict    = ConflictDetector()
        self._utilization = UtilizationTracker()

    # ── Public API ─────────────────────────────────────────────────────────

    def allocate(
        self,
        vessel: VesselRequest,
        berths: list[BerthSlot],
        weights: Optional[dict[str, float]] = None,   # §3
    ) -> AllocationResult:
        """
        Allocate the optimal berth for a single vessel.

        Parameters
        ----------
        vessel  : VesselRequest containing ETA model outputs + vessel features.
        berths  : Candidate BerthSlot pool.
        weights : §3 Optional per-call scoring weight override.

        Returns
        -------
        AllocationResult with full scheduling and KPI output.
        """
        alerts: list[str] = []

        # §8: Pre-filter berths to the vessel's destination port so that both
        # hard-constraint filtering AND fallback paths only see the correct port.
        if vessel.port_id:
            port_prefix = vessel.port_id.upper() + "_"
            port_berths = [b for b in berths if b.berth_id.upper().startswith(port_prefix)]
            # If no berths at all exist for this port, fall back to the full pool
            # (avoids a HOLD placeholder for a valid port with zero dataset entries)
            berths = port_berths if port_berths else berths

        # Step 1 – hard constraint filter
        feasible, rejection_reasons = self._validator.filter_feasible_berths(vessel, berths)

        if not feasible:
            return self._fallback_allocation(vessel, berths, rejection_reasons)

        if rejection_reasons:
            alerts.append(f"⚠ {len(rejection_reasons)} berth(s) rejected by constraints")

        # Step 2 – score all candidates
        # §9: Priority vessels receive a score boost so they always get the
        # highest-ranked berth.  Emergency vessels (priority=2) also ignore
        # queue length — they are allocated immediately regardless of queue.
        # each entry: (berth, wait_min, start_dt, service_h, score)
        priority_multiplier = 1.0 + vessel.priority * 0.30   # 1.0 / 1.3 / 1.6

        candidates: list[tuple[BerthSlot, float, datetime, float, float]] = []
        for berth in feasible:
            wait_min, start_dt, svc_h = self._wait_calc.compute_waiting_time(vessel, berth)
            base_score = self._scorer.score_berth(vessel, berth, wait_min, weights)
            score = float(np.clip(base_score * priority_multiplier, 0.0, 1.0))
            candidates.append((berth, wait_min, start_dt, svc_h, score))

        candidates.sort(key=lambda x: x[4], reverse=True)   # best score first

        # Step 3 – conflict resolution §1
        final_berth: Optional[BerthSlot]    = None
        final_wait:  float                  = 0.0
        final_start: datetime               = datetime.utcnow()
        final_departure: datetime           = datetime.utcnow()
        final_score:  float                 = 0.0
        final_svc_h:  float                 = vessel.estimated_service_time_hours
        conflict_flag: bool                 = False

        for berth, wait_min, start_dt, svc_h, score in candidates:
            departure_dt = start_dt + timedelta(hours=svc_h)
            has_conflict = self._conflict.detect_conflict(
                berth.berth_id, start_dt, departure_dt, self._active_allocations
            )

            if not has_conflict:
                final_berth, final_wait, final_start  = berth, wait_min, start_dt
                final_departure, final_score, final_svc_h = departure_dt, score, svc_h
                conflict_flag = False
                break

            # §1: try rescheduling
            new_start, resolved = self._resolve_conflict(
                berth.berth_id, start_dt, departure_dt, self._active_allocations
            )
            if resolved:
                adj_wait, adj_departure = self._wait_calc.compute_waiting_time_from_start(
                    vessel, new_start, svc_h
                )
                if adj_wait <= self.MAX_WAIT_FOR_CONFLICT_RESOLUTION:
                    adj_score = self._scorer.score_berth(vessel, berth, adj_wait, weights)
                    alerts.append(
                        f"✓ Conflict resolved: rescheduled to "
                        f"{new_start.strftime('%H:%M')} at berth {berth.berth_id} "
                        f"(+{adj_wait - wait_min:.0f} min extra wait)"
                    )
                    final_berth    = berth
                    final_wait     = adj_wait
                    final_start    = new_start
                    final_departure = adj_departure
                    final_score    = adj_score
                    final_svc_h    = svc_h
                    conflict_flag  = False
                    break

        # All candidates had unresolvable conflicts
        if final_berth is None:
            b0, w0, s0, sv0, sc0 = candidates[0]
            final_berth, final_wait, final_start = b0, w0, s0
            final_departure = s0 + timedelta(hours=sv0)
            final_score, final_svc_h = sc0, sv0
            conflict_flag = True
            alerts.append(
                f"🚨 Rescheduling failed for all candidates: "
                f"conflict retained at berth {final_berth.berth_id}"
            )

        # Step 4 – utilization
        utilization = self._utilization.compute_utilization(
            final_berth.berth_id, self._active_allocations
        )

        # Step 5 – operational alerts
        if vessel.priority == 2:
            alerts.append("🚨 EMERGENCY VESSEL: priority allocation applied — queue bypass active")
        elif vessel.priority == 1:
            alerts.append("⚡ PRIORITY VESSEL: commercial priority allocation applied")
        if vessel.port_congestion_index >= self.CONGESTION_ALERT_THRESHOLD:
            alerts.append(f"⚠ HIGH CONGESTION: index={vessel.port_congestion_index:.2f}")
        if final_wait >= self.HIGH_WAIT_ALERT_MINUTES:
            alerts.append(
                f"⚠ LONG WAIT: {final_wait:.0f} min at berth {final_berth.berth_id}"
            )
        if vessel.wave_height_m >= 3.0:
            alerts.append(f"⚠ ROUGH SEAS: {vessel.wave_height_m:.1f}m waves — shelter-scored allocation applied")

        # Step 6 – build and register result
        result = AllocationResult(
            request_id=vessel.request_id,
            vessel_id=vessel.vessel_id,
            assigned_berth=final_berth.berth_id,
            berthing_start_time=final_start.isoformat(),
            waiting_time_minutes=round(final_wait, 1),
            departure_time=final_departure.isoformat(),
            berth_utilization=utilization,
            allocation_score=final_score,
            service_duration_hours=final_svc_h,
            congestion_flag=vessel.port_congestion_index >= self.CONGESTION_ALERT_THRESHOLD,
            conflict_flag=conflict_flag,
            alert_messages=alerts,
        )
        self._active_allocations.append(result)
        return result

    def allocate_batch(
        self,
        vessels: list[VesselRequest],
        berths: list[BerthSlot],
        weights: Optional[dict[str, float]] = None,
    ) -> list[AllocationResult]:
        """
        §5: Greedy batch allocation – processes vessels earliest-ETA first.

        Each vessel is allocated via the single ``allocate()`` method, which
        automatically accounts for conflicts created by earlier vessels in this
        batch (since they are registered in _active_allocations first).

        Parameters
        ----------
        vessels : List of VesselRequest (need not be pre-sorted).
        berths  : Shared berth pool for all vessels.
        weights : Optional per-call weight override passed to allocate().

        Returns
        -------
        List of AllocationResult in the **same order** as input vessels.
        """
        # §9: Sort by descending priority first, then by earliest ETA.
        # This ensures emergency/priority vessels are allocated before normal ones
        # and thus see fewer conflicts from earlier-processed vessels.
        indexed = list(enumerate(vessels))
        indexed.sort(key=lambda iv: (-iv[1].priority, pd.to_datetime(iv[1].predicted_eta)))

        results_by_idx: dict[int, AllocationResult] = {}
        for orig_idx, vessel in indexed:
            results_by_idx[orig_idx] = self.allocate(vessel, berths, weights)

        return [results_by_idx[i] for i in range(len(vessels))]

    def update_allocation(
        self,
        request_id: str,
        new_berth_id: Optional[str] = None,
        new_start_time: Optional[datetime] = None,
    ) -> AllocationResult:
        """
        §7: Update an existing allocation by request_id.

        Mutates the stored record in-place, re-evaluates conflict_flag, and
        appends an audit entry to alert_messages.

        Parameters
        ----------
        request_id     : The request_id of the allocation to modify.
        new_berth_id   : If provided, changes the assigned berth.
        new_start_time : If provided, recalculates start, wait, and departure.

        Raises
        ------
        ValueError if request_id is not found.
        """
        for i, alloc in enumerate(self._active_allocations):
            if alloc.request_id != request_id:
                continue

            if new_berth_id is not None:
                alloc.assigned_berth = new_berth_id

            if new_start_time is not None:
                original_eta = (
                    pd.to_datetime(alloc.berthing_start_time)
                    - timedelta(minutes=alloc.waiting_time_minutes)
                )
                new_wait   = max(0.0, (new_start_time - original_eta).total_seconds() / 60)
                new_depart = new_start_time + timedelta(hours=alloc.service_duration_hours)
                alloc.berthing_start_time  = new_start_time.isoformat()
                alloc.waiting_time_minutes = round(new_wait, 1)
                alloc.departure_time       = new_depart.isoformat()

            # Re-check conflicts (exclude self)
            others     = [a for j, a in enumerate(self._active_allocations) if j != i]
            start_dt   = pd.to_datetime(alloc.berthing_start_time)
            end_dt     = pd.to_datetime(alloc.departure_time)
            alloc.conflict_flag = self._conflict.detect_conflict(
                alloc.assigned_berth, start_dt, end_dt, others
            )
            alloc.alert_messages.append(
                f"✏ Updated at {datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')}"
            )
            self._active_allocations[i] = alloc
            return alloc

        raise ValueError(f"No allocation found with request_id='{request_id}'")

    def get_active_allocations(self) -> list[AllocationResult]:
        """Return all active allocations (for dashboard / API)."""
        return list(self._active_allocations)

    def get_berth_status(self, berths: list[BerthSlot]) -> list[dict]:
        """
        Summarise current utilization and queue for all berths.
        Used by GET /berth-status endpoint.
        """
        now = datetime.utcnow()
        status = []
        for berth in berths:
            util  = self._utilization.compute_utilization(berth.berth_id, self._active_allocations, now)
            queue = sum(
                1 for a in self._active_allocations
                if a.assigned_berth == berth.berth_id and pd.to_datetime(a.departure_time) > now
            )
            status.append({
                "berth_id": berth.berth_id,
                "berth_max_length": berth.berth_max_length,
                "berth_max_draft": berth.berth_max_draft,
                "crane_availability_ratio": berth.crane_availability_ratio,
                "current_queue": queue,
                "utilization": util,
                "available_from": berth.berth_available_from,
            })
        return status

    def get_port_kpis(self) -> dict:
        """
        Compute aggregate port-level KPIs.
        Used by GET /port-kpis endpoint.
        """
        if not self._active_allocations:
            return {
                "total_allocations": 0,
                "avg_waiting_time_minutes": 0.0,
                "avg_berth_utilization": 0.0,
                "conflict_count": 0,
                "congestion_count": 0,
                "active_vessels": 0,
            }

        now       = datetime.utcnow()
        active    = [a for a in self._active_allocations if pd.to_datetime(a.departure_time) > now]
        avg_wait  = np.mean([a.waiting_time_minutes for a in self._active_allocations])
        avg_util  = np.mean([a.berth_utilization for a in self._active_allocations])
        conflicts = sum(1 for a in self._active_allocations if a.conflict_flag)
        cong      = sum(1 for a in self._active_allocations if a.congestion_flag)

        return {
            "total_allocations": len(self._active_allocations),
            "avg_waiting_time_minutes": round(float(avg_wait), 1),
            "avg_berth_utilization": round(float(avg_util), 3),
            "conflict_count": conflicts,
            "congestion_count": cong,
            "active_vessels": len(active),
        }

    def clear_expired_allocations(self, cutoff_hours: int = 48) -> int:
        """Remove allocations whose departure is older than cutoff_hours."""
        now    = datetime.utcnow()
        cutoff = now - timedelta(hours=cutoff_hours)
        before = len(self._active_allocations)
        self._active_allocations = [
            a for a in self._active_allocations
            if pd.to_datetime(a.departure_time) > cutoff
        ]
        return before - len(self._active_allocations)

    # ── Internal helpers ───────────────────────────────────────────────────

    def _resolve_conflict(
        self,
        berth_id: str,
        proposed_start: datetime,
        proposed_end: datetime,
        active_allocations: list[AllocationResult],
    ) -> tuple[datetime, bool]:
        """
        §1: Reschedule by pushing start to the latest conflicting departure.

        Collects all allocations at berth_id that overlap [proposed_start, proposed_end).
        Returns (new_start, True) where new_start = max of their departure times.
        Returns (proposed_start, True) if no overlap is found (guard against races).
        """
        conflicting_ends: list[datetime] = []
        for alloc in active_allocations:
            if alloc.assigned_berth != berth_id:
                continue
            ex_start = pd.to_datetime(alloc.berthing_start_time)
            ex_end   = pd.to_datetime(alloc.departure_time)
            if proposed_start < ex_end and proposed_end > ex_start:
                conflicting_ends.append(ex_end)

        if not conflicting_ends:
            return proposed_start, True

        return max(conflicting_ends), True

    def _fallback_allocation(
        self,
        vessel: VesselRequest,
        berths: list[BerthSlot],
        reasons: list[str],
    ) -> AllocationResult:
        """
        §4: Improved fallback when no berth passes hard constraints.

        Priority:
            1. Soft-constraint candidates (within LOA 5% + draft 0.5 m tolerance)
               → pick the one with lowest waiting time
            2. Largest berth with 2-hour padding (no soft match)
            3. HOLD placeholder (no berths at all)
        """
        alerts = ["🚨 NO FEASIBLE BERTH: fallback allocation applied"]

        soft_candidates = self._validator.filter_soft_fallback(vessel, berths)

        if soft_candidates:
            best: Optional[tuple[BerthSlot, float, datetime, float, list[str]]] = None
            for berth, violations in soft_candidates:
                wait_min, start_dt, svc_h = self._wait_calc.compute_waiting_time(vessel, berth)
                if best is None or wait_min < best[1]:
                    best = (berth, wait_min, start_dt, svc_h, violations)

            assert best is not None
            berth, wait_min, start_dt, svc_h, violations = best
            departure_dt = start_dt + timedelta(hours=svc_h)
            for v in violations:
                alerts.append(f"Fallback: assigned to {berth.berth_id} with {v}")

            result = AllocationResult(
                request_id=vessel.request_id,
                vessel_id=vessel.vessel_id,
                assigned_berth=berth.berth_id,
                berthing_start_time=start_dt.isoformat(),
                waiting_time_minutes=round(wait_min, 1),
                departure_time=departure_dt.isoformat(),
                berth_utilization=self._utilization.compute_utilization(
                    berth.berth_id, self._active_allocations
                ),
                allocation_score=0.0,
                service_duration_hours=svc_h,
                congestion_flag=True,
                conflict_flag=True,
                alert_messages=alerts + reasons[:2],
            )

        elif berths:
            fb = max(berths, key=lambda b: b.berth_max_length)
            now = datetime.utcnow()
            start = now + timedelta(hours=2)
            svc_h = vessel.estimated_service_time_hours
            departure = start + timedelta(hours=svc_h)
            alerts.append(
                f"Last-resort: assigned to largest berth {fb.berth_id} "
                f"with 2-hour padding (no soft-constraint match)"
            )
            result = AllocationResult(
                request_id=vessel.request_id,
                vessel_id=vessel.vessel_id,
                assigned_berth=fb.berth_id,
                berthing_start_time=start.isoformat(),
                waiting_time_minutes=120.0,
                departure_time=departure.isoformat(),
                berth_utilization=1.0,
                allocation_score=0.0,
                service_duration_hours=svc_h,
                congestion_flag=True,
                conflict_flag=True,
                alert_messages=alerts + reasons[:2],
            )

        else:
            now = datetime.utcnow()
            result = AllocationResult(
                request_id=vessel.request_id,
                vessel_id=vessel.vessel_id,
                assigned_berth="HOLD",
                berthing_start_time=(now + timedelta(hours=2)).isoformat(),
                waiting_time_minutes=120.0,
                departure_time=(
                    now + timedelta(hours=2 + vessel.estimated_service_time_hours)
                ).isoformat(),
                berth_utilization=1.0,
                allocation_score=0.0,
                service_duration_hours=vessel.estimated_service_time_hours,
                congestion_flag=True,
                conflict_flag=True,
                alert_messages=[
                    "🚨 HOLD: no berths registered in system. "
                    "Configure berths before allocating vessels."
                ],
            )

        self._active_allocations.append(result)
        return result
