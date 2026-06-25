"""add_work_orders_and_auth_features

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-14 12:00:00.000000

Adds:
  - work_orders table (auto-generated port operations tasks)
  - users.port_id FK (port-restricted access per IAM FR 1.8)
  - users.is_mfa_enabled flag (for future MFA IAM FR 1.3)
  - api_keys.scopes column (granular permission scopes)
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Create work_orders enum types ─────────────────────────────────────────
    work_order_type = sa.Enum(
        "mooring", "unmooring", "pilotage", "tugboat", "cargo_handling",
        "customs_inspection", "health_inspection", "bunkering",
        "fresh_water", "waste_reception", "maintenance", "general",
        name="workordertype",
    )
    work_order_status = sa.Enum(
        "pending", "assigned", "in_progress", "completed", "cancelled",
        name="workorderstatus",
    )
    work_order_priority = sa.Enum(
        "low", "normal", "high", "urgent",
        name="workorderpriority",
    )

    # ── Create work_orders table ───────────────────────────────────────────────
    op.create_table(
        "work_orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("visit_id", sa.Integer(), sa.ForeignKey("visits.id"), nullable=False),
        sa.Column("berth_id", sa.Integer(), sa.ForeignKey("berths.id"), nullable=True),
        sa.Column("vessel_id", sa.Integer(), sa.ForeignKey("vessels.id"), nullable=False),
        sa.Column("assigned_to", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("order_type", work_order_type, nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", work_order_status, nullable=False, server_default="pending"),
        sa.Column("priority", work_order_priority, nullable=False, server_default="normal"),
        sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scheduled_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completion_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_work_orders_id", "work_orders", ["id"])
    op.create_index("ix_work_orders_visit_id", "work_orders", ["visit_id"])
    op.create_index("ix_work_orders_vessel_id", "work_orders", ["vessel_id"])
    op.create_index("ix_work_orders_berth_id", "work_orders", ["berth_id"])

    # ── Extend users table ────────────────────────────────────────────────────
    op.add_column(
        "users",
        sa.Column("port_id", sa.Integer(), sa.ForeignKey("ports.id"), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("is_mfa_enabled", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_users_port_id", "users", ["port_id"])

    # ── Extend api_keys table ─────────────────────────────────────────────────
    op.add_column(
        "api_keys",
        sa.Column("scopes", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    # Reverse api_keys extension
    op.drop_column("api_keys", "scopes")

    # Reverse users extension
    op.drop_index("ix_users_port_id", table_name="users")
    op.drop_column("users", "is_mfa_enabled")
    op.drop_column("users", "port_id")

    # Drop work_orders table
    op.drop_index("ix_work_orders_berth_id", table_name="work_orders")
    op.drop_index("ix_work_orders_vessel_id", table_name="work_orders")
    op.drop_index("ix_work_orders_visit_id", table_name="work_orders")
    op.drop_index("ix_work_orders_id", table_name="work_orders")
    op.drop_table("work_orders")

    # Drop enum types
    sa.Enum(name="workorderpriority").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="workorderstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="workordertype").drop(op.get_bind(), checkfirst=True)
