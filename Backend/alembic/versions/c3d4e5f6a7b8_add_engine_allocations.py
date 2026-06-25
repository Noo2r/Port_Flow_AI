"""add_engine_allocations

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-20 00:00:00.000000

Adds engine_allocations table so BerthOptimizationEngine active-allocation
state survives restarts and conflict detection stays correct for docked vessels.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "engine_allocations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.String(length=50), nullable=False),
        sa.Column("vessel_id", sa.String(length=100), nullable=False),
        sa.Column("assigned_berth", sa.String(length=100), nullable=False),
        sa.Column("berthing_start_time", sa.DateTime(timezone=False), nullable=False),
        sa.Column("waiting_time_minutes", sa.Float(), nullable=False),
        sa.Column("departure_time", sa.DateTime(timezone=False), nullable=False),
        sa.Column("berth_utilization", sa.Float(), nullable=False),
        sa.Column("allocation_score", sa.Float(), nullable=False),
        sa.Column("service_duration_hours", sa.Float(), nullable=False),
        sa.Column("congestion_flag", sa.Boolean(), nullable=False),
        sa.Column("conflict_flag", sa.Boolean(), nullable=False),
        sa.Column("alert_messages", sa.JSON(), nullable=False),
        sa.Column(
            "allocated_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id"),
    )
    op.create_index(op.f("ix_engine_allocations_id"), "engine_allocations", ["id"], unique=False)
    op.create_index(
        op.f("ix_engine_allocations_request_id"), "engine_allocations", ["request_id"], unique=True
    )
    op.create_index(
        op.f("ix_engine_allocations_vessel_id"), "engine_allocations", ["vessel_id"], unique=False
    )
    op.create_index(
        op.f("ix_engine_allocations_departure_time"),
        "engine_allocations",
        ["departure_time"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_engine_allocations_departure_time"), table_name="engine_allocations")
    op.drop_index(op.f("ix_engine_allocations_vessel_id"), table_name="engine_allocations")
    op.drop_index(op.f("ix_engine_allocations_request_id"), table_name="engine_allocations")
    op.drop_index(op.f("ix_engine_allocations_id"), table_name="engine_allocations")
    op.drop_table("engine_allocations")
