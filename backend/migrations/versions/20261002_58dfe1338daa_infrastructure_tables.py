"""Infrastructure tables: jobs, outbox, worker heartbeats, idempotency keys (E1a).

Revision ID: 58dfe1338daa
Revises:
Create Date: 2026-10-02

Staged migration note: ``idempotency_keys.user_id`` intentionally has no
foreign key yet. The ``users`` table arrives in E2, whose migration adds
``fk_idempotency_keys_user_id_users`` (see docs/backend-foundation.md).
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "58dfe1338daa"
down_revision = None
branch_labels = None
depends_on = None

job_status = postgresql.ENUM(
    "QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "DEAD", name="job_status", create_type=False
)


def upgrade() -> None:
    job_status.create(op.get_bind(), checkfirst=False)

    op.create_table(
        "jobs",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("job_type", sa.String(length=100), nullable=False),
        sa.Column(
            "payload", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", job_status, server_default="QUEUED", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default="5", nullable=False),
        sa.Column("locked_by", sa.String(length=200), nullable=True),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("dedupe_key", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("attempts >= 0", name=op.f("ck_jobs_attempts_non_negative")),
        sa.CheckConstraint("max_attempts >= 1", name=op.f("ck_jobs_max_attempts_positive")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
        sa.UniqueConstraint("dedupe_key", name=op.f("uq_jobs_dedupe_key")),
    )
    op.create_index(
        "ix_jobs_claimable",
        "jobs",
        ["run_at", "id"],
        postgresql_where=sa.text("status IN ('QUEUED', 'FAILED')"),
    )
    op.create_index(
        "ix_jobs_running_locked_until",
        "jobs",
        ["locked_until"],
        postgresql_where=sa.text("status = 'RUNNING'"),
    )

    op.create_table(
        "outbox_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("aggregate_type", sa.String(length=100), nullable=False),
        sa.Column("aggregate_id", sa.Uuid(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outbox_events")),
    )
    op.create_index(
        "ix_outbox_events_unprocessed",
        "outbox_events",
        ["id"],
        postgresql_where=sa.text("processed_at IS NULL"),
    )

    op.create_table(
        "worker_heartbeats",
        sa.Column("worker_id", sa.String(length=200), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("worker_id", name=op.f("pk_worker_heartbeats")),
    )
    op.create_index(
        op.f("ix_worker_heartbeats_last_seen_at"), "worker_heartbeats", ["last_seen_at"]
    )

    op.create_table(
        "idempotency_keys",
        sa.Column("user_id", sa.Uuid(), nullable=False),  # FK to users added in E2
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("endpoint", sa.String(length=200), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("response_body", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "char_length(key) BETWEEN 8 AND 255", name=op.f("ck_idempotency_keys_key_length")
        ),
        sa.PrimaryKeyConstraint("user_id", "key", name=op.f("pk_idempotency_keys")),
    )
    op.create_index("ix_idempotency_keys_expires_at", "idempotency_keys", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_idempotency_keys_expires_at", table_name="idempotency_keys")
    op.drop_table("idempotency_keys")
    op.drop_index(op.f("ix_worker_heartbeats_last_seen_at"), table_name="worker_heartbeats")
    op.drop_table("worker_heartbeats")
    op.drop_index("ix_outbox_events_unprocessed", table_name="outbox_events")
    op.drop_table("outbox_events")
    op.drop_index("ix_jobs_running_locked_until", table_name="jobs")
    op.drop_index("ix_jobs_claimable", table_name="jobs")
    op.drop_table("jobs")
    job_status.drop(op.get_bind(), checkfirst=False)
