"""Initial schema for workflow history tables.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-02-09 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_runs",
        sa.Column("repo", sa.Text(), nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("run_number", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("conclusion", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.Column("head_sha", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("repo", "run_id", name="pk_workflow_runs"),
    )
    op.create_table(
        "step_durations",
        sa.Column("repo", sa.Text(), nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("step_name", sa.Text(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(
            ["repo", "run_id"],
            ["workflow_runs.repo", "workflow_runs.run_id"],
            name="fk_step_durations_workflow_runs",
        ),
        sa.PrimaryKeyConstraint("repo", "run_id", "step_name", name="pk_step_durations"),
    )
    op.create_table(
        "test_durations",
        sa.Column("repo", sa.Text(), nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("test_name", sa.Text(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(
            ["repo", "run_id"],
            ["workflow_runs.repo", "workflow_runs.run_id"],
            name="fk_test_durations_workflow_runs",
        ),
        sa.PrimaryKeyConstraint("repo", "run_id", "test_name", name="pk_test_durations"),
    )
    op.create_table(
        "test_outcomes",
        sa.Column("repo", sa.Text(), nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("test_name", sa.Text(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["repo", "run_id"],
            ["workflow_runs.repo", "workflow_runs.run_id"],
            name="fk_test_outcomes_workflow_runs",
        ),
        sa.PrimaryKeyConstraint("repo", "run_id", "test_name", name="pk_test_outcomes"),
    )


def downgrade() -> None:
    op.drop_table("test_outcomes")
    op.drop_table("test_durations")
    op.drop_table("step_durations")
    op.drop_table("workflow_runs")
