"""
Regression tests for Phase 2.5 berth-occupancy fixes:

1. app.api.v1.endpoints.eta._release_berth_if_unused — releases the old
   berth when a visit is reassigned to a new one (Bug #1: berth reassignment leak).
2. app.services.berth_reconciliation.reconcile_berth_occupancy — self-heals
   any berth left OCCUPIED with zero active visits (Bug #2: stale occupancy).

Pure unit tests using a lightweight fake AsyncSession — no live DB needed.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.v1.endpoints.eta import _release_berth_if_unused
from app.models.berth import Berth, BerthStatus
from app.services.berth_reconciliation import reconcile_berth_occupancy


def _fake_berth(id_: int, code: str, status: BerthStatus) -> MagicMock:
    b = MagicMock(spec=Berth)
    b.id = id_
    b.code = code
    b.status = status
    return b


class _FakeSession:
    """Minimal AsyncSession stand-in with scriptable execute()/get() results."""

    def __init__(self, scalar_result=0, scalars_all_result=None, all_result=None, get_result=None):
        self._scalar_result = scalar_result
        self._scalars_all_result = scalars_all_result or []
        self._all_result = all_result or []
        self._get_result = get_result
        self.committed = False

    async def execute(self, _query):
        result = MagicMock()
        result.scalar.return_value = self._scalar_result
        result.scalars.return_value.all.return_value = self._scalars_all_result
        result.all.return_value = self._all_result
        return result

    async def get(self, _model, _id):
        return self._get_result

    async def commit(self):
        self.committed = True


# ── Bug #1: eta.py's _release_berth_if_unused ──────────────────────────────────

class TestReleaseBerthIfUnused:
    @pytest.mark.asyncio
    async def test_releases_when_no_active_visits_remain(self):
        berth = _fake_berth(4, "PORT_A_B02", BerthStatus.OCCUPIED)
        db = _FakeSession(scalar_result=0, get_result=berth)  # 0 = no active visits left

        await _release_berth_if_unused(db, berth_id=4, exclude_visit_id=12001)

        assert berth.status == BerthStatus.AVAILABLE

    @pytest.mark.asyncio
    async def test_does_not_release_when_another_active_visit_exists(self):
        berth = _fake_berth(4, "PORT_A_B02", BerthStatus.OCCUPIED)
        db = _FakeSession(scalar_result=1, get_result=berth)  # 1 = still in use

        await _release_berth_if_unused(db, berth_id=4, exclude_visit_id=12001)

        assert berth.status == BerthStatus.OCCUPIED

    @pytest.mark.asyncio
    async def test_noop_when_berth_id_is_none(self):
        db = _FakeSession()
        db.execute = AsyncMock(side_effect=AssertionError("should not query when berth_id is None"))

        await _release_berth_if_unused(db, berth_id=None)  # must not raise

    @pytest.mark.asyncio
    async def test_noop_when_berth_already_available(self):
        berth = _fake_berth(4, "PORT_A_B02", BerthStatus.AVAILABLE)
        db = _FakeSession(scalar_result=0, get_result=berth)

        await _release_berth_if_unused(db, berth_id=4)

        assert berth.status == BerthStatus.AVAILABLE  # unchanged, not an error


# ── Bug #2: berth_reconciliation.reconcile_berth_occupancy ─────────────────────

class TestReconcileBerthOccupancy:
    @pytest.mark.asyncio
    async def test_releases_stale_occupied_berth_with_no_active_visit(self):
        stale = _fake_berth(50, "PORT_E_B00", BerthStatus.OCCUPIED)
        db = _FakeSession(scalars_all_result=[stale], all_result=[])  # no active visits reference berth 50

        result = await reconcile_berth_occupancy(db)

        assert stale.status == BerthStatus.AVAILABLE
        assert result == {"checked": 1, "released": 1, "released_berth_codes": ["PORT_E_B00"]}
        assert db.committed is True

    @pytest.mark.asyncio
    async def test_preserves_legitimately_occupied_berth(self):
        legit = _fake_berth(2, "PORT_A_B00", BerthStatus.OCCUPIED)
        db = _FakeSession(scalars_all_result=[legit], all_result=[(2,)])  # an active visit references berth 2

        result = await reconcile_berth_occupancy(db)

        assert legit.status == BerthStatus.OCCUPIED
        assert result == {"checked": 1, "released": 0, "released_berth_codes": []}
        assert db.committed is False  # no-op commit skipped

    @pytest.mark.asyncio
    async def test_mixed_batch_releases_only_the_stale_one(self):
        legit = _fake_berth(2, "PORT_A_B00", BerthStatus.OCCUPIED)
        stale = _fake_berth(50, "PORT_E_B00", BerthStatus.OCCUPIED)
        db = _FakeSession(scalars_all_result=[legit, stale], all_result=[(2,)])

        result = await reconcile_berth_occupancy(db)

        assert legit.status == BerthStatus.OCCUPIED
        assert stale.status == BerthStatus.AVAILABLE
        assert result["checked"] == 2
        assert result["released"] == 1
        assert result["released_berth_codes"] == ["PORT_E_B00"]

    @pytest.mark.asyncio
    async def test_noop_when_no_berths_occupied(self):
        db = _FakeSession(scalars_all_result=[])

        result = await reconcile_berth_occupancy(db)

        assert result == {"checked": 0, "released": 0, "released_berth_codes": []}
        assert db.committed is False
