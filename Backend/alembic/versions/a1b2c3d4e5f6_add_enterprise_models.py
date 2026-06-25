"""add_enterprise_models

Revision ID: a1b2c3d4e5f6
Revises: e034336fbdef
Create Date: 2026-03-14 00:00:00.000000

Adds all enterprise domain tables and extends existing core tables with
new columns for port association, voyage tracking, and richer metadata.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "e034336fbdef"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. New standalone/root tables (no deps on new tables) ───────────────

    op.create_table(
        "ports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=10), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("timezone", sa.String(length=50), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("un_locode", sa.String(length=10), nullable=True),
        sa.Column("max_vessel_loa", sa.Float(), nullable=True),
        sa.Column("max_vessel_draft", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ports_id"), "ports", ["id"], unique=False)
    op.create_index(op.f("ix_ports_code"), "ports", ["code"], unique=True)

    op.create_table(
        "terminals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("port_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("terminal_type", sa.String(length=50), nullable=True),
        sa.Column("operator", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["port_id"], ["ports.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_terminals_id"), "terminals", ["id"], unique=False)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=True),
        sa.Column("role", sa.Enum("ADMIN", "PORT_MANAGER", "VESSEL_AGENT", "OPERATIONS", "ANALYST", "READONLY", name="userrole"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("key_hash", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_api_keys_id"), "api_keys", ["id"], unique=False)

    op.create_table(
        "audit_trails",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=50), nullable=True),
        sa.Column("resource_id", sa.Integer(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_trails_id"), "audit_trails", ["id"], unique=False)
    op.create_index(op.f("ix_audit_trails_user_id"), "audit_trails", ["user_id"], unique=False)

    op.create_table(
        "ai_model_registry",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("model_version", sa.String(length=30), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("input_format", sa.JSON(), nullable=True),
        sa.Column("output_format", sa.JSON(), nullable=True),
        sa.Column("training_data_start", sa.Date(), nullable=True),
        sa.Column("training_data_end", sa.Date(), nullable=True),
        sa.Column("training_samples", sa.Integer(), nullable=True),
        sa.Column("accuracy_score", sa.Float(), nullable=True),
        sa.Column("mae_score", sa.Float(), nullable=True),
        sa.Column("rmse_score", sa.Float(), nullable=True),
        sa.Column("r2_score", sa.Float(), nullable=True),
        sa.Column("approval_status", sa.Enum("DRAFT", "UNDER_REVIEW", "APPROVED", "DEPRECATED", "REJECTED", name="modelapprovalstatus"), nullable=False),
        sa.Column("deployment_env", sa.Enum("DEVELOPMENT", "STAGING", "PRODUCTION", name="deploymentenvironment"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("deployed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deprecated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_model_registry_id"), "ai_model_registry", ["id"], unique=False)
    op.create_index(op.f("ix_ai_model_registry_model_name"), "ai_model_registry", ["model_name"], unique=False)

    op.create_table(
        "notification_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("channel", sa.Enum("EMAIL", "SMS", "WEBHOOK", "IN_APP", name="notificationchannel"), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=True),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notification_templates_id"), "notification_templates", ["id"], unique=False)

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=True),
        sa.Column("recipient", sa.String(length=255), nullable=False),
        sa.Column("channel", sa.Enum("EMAIL", "SMS", "WEBHOOK", "IN_APP", name="notificationchannel"), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "SENT", "FAILED", "READ", name="notificationstatus"), nullable=False),
        sa.Column("reference_type", sa.String(length=50), nullable=True),
        sa.Column("reference_id", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["template_id"], ["notification_templates.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notifications_id"), "notifications", ["id"], unique=False)

    op.create_table(
        "kpi_definitions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.Enum("EFFICIENCY", "SAFETY", "ENVIRONMENTAL", "FINANCIAL", "OPERATIONAL", name="kpicategory"), nullable=False),
        sa.Column("unit", sa.String(length=30), nullable=True),
        sa.Column("target_value", sa.Float(), nullable=True),
        sa.Column("is_higher_better", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_kpi_definitions_id"), "kpi_definitions", ["id"], unique=False)

    op.create_table(
        "kpi_values",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kpi_id", sa.Integer(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_kpi_values_id"), "kpi_values", ["id"], unique=False)

    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("report_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.Enum("DRAFT", "GENERATED", "PUBLISHED", "ARCHIVED", name="reportstatus"), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.Column("file_path", sa.String(length=500), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reports_id"), "reports", ["id"], unique=False)

    op.create_table(
        "aast_research_projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_code", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("institution", sa.String(length=200), nullable=False),
        sa.Column("principal_investigator", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.Enum("PROPOSED", "ACTIVE", "COMPLETED", "PAUSED", "CANCELLED", name="researchstatus"), nullable=False),
        sa.Column("data_access_level", sa.Enum("AGGREGATED", "ANONYMIZED", "FULL", name="dataaccesslevel"), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("ethics_approval", sa.Boolean(), nullable=False),
        sa.Column("ethics_reference", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_aast_research_projects_id"), "aast_research_projects", ["id"], unique=False)

    op.create_table(
        "research_findings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("publication_url", sa.String(length=500), nullable=True),
        sa.Column("published_at", sa.Date(), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["aast_research_projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_research_findings_id"), "research_findings", ["id"], unique=False)

    op.create_table(
        "research_data_access",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("dataset", sa.String(length=100), nullable=False),
        sa.Column("access_level", sa.Enum("AGGREGATED", "ANONYMIZED", "FULL", name="dataaccesslevel"), nullable=False),
        sa.Column("records_accessed", sa.Integer(), nullable=True),
        sa.Column("accessed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("purpose", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["aast_research_projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_research_data_access_id"), "research_data_access", ["id"], unique=False)

    # ── 2. Extend existing core tables ───────────────────────────────────────

    # berths: add port_id FK + new capability/operational columns
    op.add_column("berths", sa.Column("port_id", sa.Integer(), nullable=True))
    op.add_column("berths", sa.Column("has_cold_ironing", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("berths", sa.Column("has_fresh_water", sa.Boolean(), nullable=False, server_default="true"))
    op.add_column("berths", sa.Column("has_bunker_facility", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("berths", sa.Column("priority_level", sa.Integer(), nullable=False, server_default="5"))
    op.add_column("berths", sa.Column("quay_length", sa.Float(), nullable=True))
    op.create_foreign_key("fk_berths_port_id", "berths", "ports", ["port_id"], ["id"])
    op.create_index(op.f("ix_berths_port_id"), "berths", ["port_id"], unique=False)

    # vessels: add port_id FK + commercial / research / insurance columns
    op.add_column("vessels", sa.Column("current_port_id", sa.Integer(), nullable=True))
    op.add_column("vessels", sa.Column("owner", sa.String(length=200), nullable=True))
    op.add_column("vessels", sa.Column("operator", sa.String(length=200), nullable=True))
    op.add_column("vessels", sa.Column("manager", sa.String(length=200), nullable=True))
    op.add_column("vessels", sa.Column("year_built", sa.Integer(), nullable=True))
    op.add_column("vessels", sa.Column("research_category", sa.String(length=100), nullable=True))
    op.add_column("vessels", sa.Column("pni_club", sa.String(length=200), nullable=True))
    op.add_column("vessels", sa.Column("hull_insurer", sa.String(length=200), nullable=True))
    op.add_column("vessels", sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"))
    op.create_foreign_key("fk_vessels_port_id", "vessels", "ports", ["current_port_id"], ["id"])

    # ── 3. Tables that depend on ports + vessels ──────────────────────────────

    op.create_table(
        "voyages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("voyage_number", sa.String(length=50), nullable=False),
        sa.Column("vessel_id", sa.Integer(), nullable=False),
        sa.Column("origin_port_id", sa.Integer(), nullable=True),
        sa.Column("destination_port_id", sa.Integer(), nullable=True),
        sa.Column("planned_departure", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_departure", sa.DateTime(timezone=True), nullable=True),
        sa.Column("planned_arrival", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_arrival", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Enum("PLANNED", "UNDERWAY", "COMPLETED", "CANCELLED", "DIVERTED", name="voyagestatus"), nullable=False),
        sa.Column("distance_nm", sa.Float(), nullable=True),
        sa.Column("average_speed", sa.Float(), nullable=True),
        sa.Column("fuel_consumed_mt", sa.Float(), nullable=True),
        sa.Column("co2_emissions_mt", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["vessel_id"], ["vessels.id"]),
        sa.ForeignKeyConstraint(["origin_port_id"], ["ports.id"]),
        sa.ForeignKeyConstraint(["destination_port_id"], ["ports.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_voyages_id"), "voyages", ["id"], unique=False)
    op.create_index(op.f("ix_voyages_voyage_number"), "voyages", ["voyage_number"], unique=True)
    op.create_index(op.f("ix_voyages_vessel_id"), "voyages", ["vessel_id"], unique=False)

    op.create_table(
        "weather_data",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("port_id", sa.Integer(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("wind_speed", sa.Float(), nullable=True),
        sa.Column("wind_direction", sa.Float(), nullable=True),
        sa.Column("visibility", sa.Float(), nullable=True),
        sa.Column("wave_height", sa.Float(), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("tide_height", sa.Float(), nullable=True),
        sa.Column("current_speed", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(["port_id"], ["ports.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_weather_data_id"), "weather_data", ["id"], unique=False)
    op.create_index(op.f("ix_weather_data_port_id"), "weather_data", ["port_id"], unique=False)
    op.create_index(op.f("ix_weather_data_recorded_at"), "weather_data", ["recorded_at"], unique=False)

    op.create_table(
        "equipment",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("port_id", sa.Integer(), nullable=True),
        sa.Column("berth_id", sa.Integer(), nullable=True),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("equipment_type", sa.Enum("CRANE", "FORKLIFT", "REACH_STACKER", "TUGBOAT", "MOORING_BOAT", "CONVEYOR", "PUMP", "OTHER", name="equipmenttype"), nullable=False),
        sa.Column("capacity_tons", sa.Float(), nullable=True),
        sa.Column("manufacturer", sa.String(length=100), nullable=True),
        sa.Column("year_built", sa.Integer(), nullable=True),
        sa.Column("status", sa.Enum("AVAILABLE", "IN_USE", "MAINTENANCE", "BREAKDOWN", "RETIRED", name="equipmentstatus"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["port_id"], ["ports.id"]),
        sa.ForeignKeyConstraint(["berth_id"], ["berths.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_equipment_id"), "equipment", ["id"], unique=False)
    op.create_index(op.f("ix_equipment_port_id"), "equipment", ["port_id"], unique=False)

    op.create_table(
        "labor_shifts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("port_id", sa.Integer(), nullable=True),
        sa.Column("shift_name", sa.String(length=50), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("gang_size", sa.Integer(), nullable=False),
        sa.Column("supervisor", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["port_id"], ["ports.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_labor_shifts_id"), "labor_shifts", ["id"], unique=False)

    # ── 4. Extend visits table ───────────────────────────────────────────────
    # create_table auto-registers enums; add_column does not — create explicitly
    op.execute(sa.text(
        "CREATE TYPE clearancestatus AS ENUM "
        "('PENDING','CUSTOMS_CLEARED','PORT_CLEARED','HEALTH_CLEARED','FULLY_CLEARED','FLAGGED')"
    ))
    op.add_column("visits", sa.Column("port_id", sa.Integer(), nullable=True))
    op.add_column("visits", sa.Column("voyage_id", sa.Integer(), nullable=True))
    op.add_column("visits", sa.Column("clearance_status", sa.Enum("PENDING", "CUSTOMS_CLEARED", "PORT_CLEARED", "HEALTH_CLEARED", "FULLY_CLEARED", "FLAGGED", name="clearancestatus", create_type=False), nullable=False, server_default="PENDING"))
    op.add_column("visits", sa.Column("turnaround_hours", sa.Float(), nullable=True))
    op.add_column("visits", sa.Column("efficiency_rating", sa.Float(), nullable=True))
    op.create_foreign_key("fk_visits_port_id", "visits", "ports", ["port_id"], ["id"])
    op.create_foreign_key("fk_visits_voyage_id", "visits", "voyages", ["voyage_id"], ["id"])
    op.create_index(op.f("ix_visits_port_id"), "visits", ["port_id"], unique=False)
    op.create_index(op.f("ix_visits_voyage_id"), "visits", ["voyage_id"], unique=False)

    # ── 5. Tables that depend on visits ──────────────────────────────────────

    op.create_table(
        "cargo_manifests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("visit_id", sa.Integer(), nullable=False),
        sa.Column("manifest_number", sa.String(length=50), nullable=False),
        sa.Column("status", sa.Enum("DRAFT", "SUBMITTED", "APPROVED", "COMPLETED", name="manifeststatus"), nullable=False),
        sa.Column("total_weight_mt", sa.Float(), nullable=True),
        sa.Column("total_volume_m3", sa.Float(), nullable=True),
        sa.Column("total_teu", sa.Integer(), nullable=True),
        sa.Column("discharge_port", sa.String(length=100), nullable=True),
        sa.Column("load_port", sa.String(length=100), nullable=True),
        sa.Column("shipper", sa.String(length=150), nullable=True),
        sa.Column("consignee", sa.String(length=150), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["visit_id"], ["visits.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cargo_manifests_id"), "cargo_manifests", ["id"], unique=False)
    op.create_index(op.f("ix_cargo_manifests_visit_id"), "cargo_manifests", ["visit_id"], unique=False)

    op.create_table(
        "containers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("manifest_id", sa.Integer(), nullable=False),
        sa.Column("container_number", sa.String(length=20), nullable=False),
        sa.Column("iso_type", sa.String(length=10), nullable=True),
        sa.Column("size_ft", sa.Integer(), nullable=True),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column("is_hazmat", sa.Boolean(), nullable=False),
        sa.Column("is_reefer", sa.Boolean(), nullable=False),
        sa.Column("temperature_set", sa.Float(), nullable=True),
        sa.Column("status", sa.Enum("EXPECTED", "ON_BOARD", "DISCHARGED", "LOADED", "IN_YARD", "DEPARTED", name="containerstatus"), nullable=False),
        sa.Column("seal_number", sa.String(length=30), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["manifest_id"], ["cargo_manifests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_containers_id"), "containers", ["id"], unique=False)
    op.create_index(op.f("ix_containers_manifest_id"), "containers", ["manifest_id"], unique=False)
    op.create_index(op.f("ix_containers_container_number"), "containers", ["container_number"], unique=False)

    op.create_table(
        "bulk_cargo",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("manifest_id", sa.Integer(), nullable=False),
        sa.Column("commodity", sa.String(length=100), nullable=False),
        sa.Column("quantity_mt", sa.Float(), nullable=False),
        sa.Column("stowage_factor", sa.Float(), nullable=True),
        sa.Column("is_hazmat", sa.Boolean(), nullable=False),
        sa.Column("un_number", sa.String(length=10), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["manifest_id"], ["cargo_manifests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_bulk_cargo_id"), "bulk_cargo", ["id"], unique=False)

    op.create_table(
        "equipment_allocations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("equipment_id", sa.Integer(), nullable=False),
        sa.Column("visit_id", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("task", sa.String(length=200), nullable=True),
        sa.Column("moves_count", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipment.id"]),
        sa.ForeignKeyConstraint(["visit_id"], ["visits.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_equipment_allocations_id"), "equipment_allocations", ["id"], unique=False)
    op.create_index(op.f("ix_equipment_allocations_equipment_id"), "equipment_allocations", ["equipment_id"], unique=False)
    op.create_index(op.f("ix_equipment_allocations_visit_id"), "equipment_allocations", ["visit_id"], unique=False)

    op.create_table(
        "labor_allocations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("shift_id", sa.Integer(), nullable=False),
        sa.Column("visit_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=100), nullable=True),
        sa.Column("headcount", sa.Integer(), nullable=False),
        sa.Column("productivity_moves_ph", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["shift_id"], ["labor_shifts.id"]),
        sa.ForeignKeyConstraint(["visit_id"], ["visits.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_labor_allocations_id"), "labor_allocations", ["id"], unique=False)
    op.create_index(op.f("ix_labor_allocations_shift_id"), "labor_allocations", ["shift_id"], unique=False)
    op.create_index(op.f("ix_labor_allocations_visit_id"), "labor_allocations", ["visit_id"], unique=False)

    op.create_table(
        "vessel_emissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vessel_id", sa.Integer(), nullable=False),
        sa.Column("visit_id", sa.Integer(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("source", sa.Enum("MAIN_ENGINE", "AUXILIARY_ENGINE", "BOILER", "COLD_IRONING", name="emissionsource"), nullable=False),
        sa.Column("co2_mt", sa.Float(), nullable=True),
        sa.Column("sox_kg", sa.Float(), nullable=True),
        sa.Column("nox_kg", sa.Float(), nullable=True),
        sa.Column("pm_kg", sa.Float(), nullable=True),
        sa.Column("fuel_consumed_mt", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["vessel_id"], ["vessels.id"]),
        sa.ForeignKeyConstraint(["visit_id"], ["visits.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_vessel_emissions_id"), "vessel_emissions", ["id"], unique=False)
    op.create_index(op.f("ix_vessel_emissions_vessel_id"), "vessel_emissions", ["vessel_id"], unique=False)
    op.create_index(op.f("ix_vessel_emissions_visit_id"), "vessel_emissions", ["visit_id"], unique=False)

    op.create_table(
        "waste_management",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("visit_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.Enum("BILGE_WATER", "SLUDGE", "GARBAGE", "SEWAGE", "HAZARDOUS", name="wastecategory"), nullable=False),
        sa.Column("quantity_m3", sa.Float(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("disposal_method", sa.String(length=100), nullable=True),
        sa.Column("contractor", sa.String(length=100), nullable=True),
        sa.Column("certificate_number", sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(["visit_id"], ["visits.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_waste_management_id"), "waste_management", ["id"], unique=False)

    op.create_table(
        "anomalies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vessel_id", sa.Integer(), nullable=True),
        sa.Column("visit_id", sa.Integer(), nullable=True),
        sa.Column("anomaly_type", sa.Enum("DELAY", "EXCESSIVE_WAITING", "UNUSUAL_SPEED", "CARGO_DISCREPANCY", "BERTH_CONFLICT", "EMISSION_SPIKE", "EQUIPMENT_FAILURE", "OTHER", name="anomalytype"), nullable=False),
        sa.Column("severity", sa.Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="anomalyseverity"), nullable=False),
        sa.Column("status", sa.Enum("OPEN", "ACKNOWLEDGED", "RESOLVED", "FALSE_POSITIVE", name="anomalystatus"), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("detected_value", sa.Float(), nullable=True),
        sa.Column("expected_value", sa.Float(), nullable=True),
        sa.Column("deviation_pct", sa.Float(), nullable=True),
        sa.Column("is_automated", sa.Boolean(), nullable=False),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["vessel_id"], ["vessels.id"]),
        sa.ForeignKeyConstraint(["visit_id"], ["visits.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_anomalies_id"), "anomalies", ["id"], unique=False)
    op.create_index(op.f("ix_anomalies_vessel_id"), "anomalies", ["vessel_id"], unique=False)
    op.create_index(op.f("ix_anomalies_visit_id"), "anomalies", ["visit_id"], unique=False)

    op.create_table(
        "regulatory_compliance",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vessel_id", sa.Integer(), nullable=True),
        sa.Column("visit_id", sa.Integer(), nullable=True),
        sa.Column("regulation_code", sa.String(length=100), nullable=False),
        sa.Column("regulation_name", sa.String(length=200), nullable=False),
        sa.Column("authority", sa.String(length=150), nullable=True),
        sa.Column("status", sa.Enum("COMPLIANT", "NON_COMPLIANT", "PENDING", "EXEMPT", name="compliancestatus"), nullable=False),
        sa.Column("check_date", sa.Date(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("certificate_number", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("officer_name", sa.String(length=150), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["vessel_id"], ["vessels.id"]),
        sa.ForeignKeyConstraint(["visit_id"], ["visits.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_regulatory_compliance_id"), "regulatory_compliance", ["id"], unique=False)

    op.create_table(
        "security_incidents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vessel_id", sa.Integer(), nullable=True),
        sa.Column("visit_id", sa.Integer(), nullable=True),
        sa.Column("incident_type", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="incidentseverity"), nullable=False),
        sa.Column("status", sa.Enum("OPEN", "INVESTIGATING", "RESOLVED", "CLOSED", name="incidentstatus"), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("location", sa.String(length=200), nullable=True),
        sa.Column("reported_by", sa.String(length=150), nullable=True),
        sa.Column("is_isps_reportable", sa.Boolean(), nullable=False),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["vessel_id"], ["vessels.id"]),
        sa.ForeignKeyConstraint(["visit_id"], ["visits.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_security_incidents_id"), "security_incidents", ["id"], unique=False)

    # ── 6. Extend predictions with model registry FK ──────────────────────────
    op.add_column("predictions", sa.Column("model_registry_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_predictions_model_registry_id", "predictions", "ai_model_registry", ["model_registry_id"], ["id"])
    op.create_index(op.f("ix_predictions_model_registry_id"), "predictions", ["model_registry_id"], unique=False)


def downgrade() -> None:
    # predictions
    op.drop_index(op.f("ix_predictions_model_registry_id"), table_name="predictions")
    op.drop_constraint("fk_predictions_model_registry_id", "predictions", type_="foreignkey")
    op.drop_column("predictions", "model_registry_id")

    # dependent tables
    for tbl in ["security_incidents", "regulatory_compliance", "anomalies",
                "waste_management", "vessel_emissions", "labor_allocations",
                "equipment_allocations", "bulk_cargo", "containers", "cargo_manifests"]:
        op.drop_table(tbl)

    # visits extensions
    op.drop_index(op.f("ix_visits_voyage_id"), table_name="visits")
    op.drop_index(op.f("ix_visits_port_id"), table_name="visits")
    op.drop_constraint("fk_visits_voyage_id", "visits", type_="foreignkey")
    op.drop_constraint("fk_visits_port_id", "visits", type_="foreignkey")
    op.drop_column("visits", "efficiency_rating")
    op.drop_column("visits", "turnaround_hours")
    op.drop_column("visits", "clearance_status")
    op.drop_column("visits", "voyage_id")
    op.drop_column("visits", "port_id")

    # voyages + weather
    op.drop_table("weather_data")
    op.drop_table("labor_shifts")
    op.drop_table("equipment")
    op.drop_table("voyages")

    # vessels extensions
    op.drop_constraint("fk_vessels_port_id", "vessels", type_="foreignkey")
    for col in ["is_active", "hull_insurer", "pni_club", "research_category",
                "year_built", "manager", "operator", "owner", "current_port_id"]:
        op.drop_column("vessels", col)

    # berths extensions
    op.drop_index(op.f("ix_berths_port_id"), table_name="berths")
    op.drop_constraint("fk_berths_port_id", "berths", type_="foreignkey")
    for col in ["quay_length", "priority_level", "has_bunker_facility", "has_fresh_water",
                "has_cold_ironing", "port_id"]:
        op.drop_column("berths", col)

    # root tables
    for tbl in ["research_data_access", "research_findings", "aast_research_projects",
                "reports", "kpi_values", "kpi_definitions",
                "notifications", "notification_templates",
                "ai_model_registry", "audit_trails", "api_keys", "users",
                "terminals", "ports"]:
        op.drop_table(tbl)

    # drop enums
    for enum_name in ["userrole", "modelapprovalstatus", "deploymentenvironment",
                      "notificationchannel", "notificationstatus", "kpicategory",
                      "reportstatus", "researchstatus", "dataaccesslevel",
                      "voyagestatus", "clearancestatus", "equipmenttype", "equipmentstatus",
                      "emissionsource", "wastecategory", "anomalytype", "anomalyseverity",
                      "anomalystatus", "manifeststatus", "containerstatus",
                      "compliancestatus", "incidentseverity", "incidentstatus"]:
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
