"""Immutable journal, versioned settlements and durable notifications."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def timestamps():
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade():
    op.create_table(
        "ledger_state",
        sa.Column("group_id", sa.String(36), sa.ForeignKey("group_groups.id"), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
    )
    op.execute("INSERT INTO ledger_state (group_id, version) SELECT id, 0 FROM group_groups")
    op.add_column("ledger_settlements", sa.Column("idempotency_key", sa.String(100)))
    op.add_column("ledger_settlements", sa.Column("request_hash", sa.String(64)))
    op.add_column("ledger_settlements", sa.Column("reversal_of", sa.String(36)))
    op.create_foreign_key(
        "fk_settlement_reversal",
        "ledger_settlements",
        "ledger_settlements",
        ["reversal_of"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_settlement_retry", "ledger_settlements", ["group_id", "idempotency_key"]
    )
    op.create_unique_constraint("uq_settlement_reversal", "ledger_settlements", ["reversal_of"])
    op.create_table(
        "ledger_journal",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("group_id", sa.String(36), sa.ForeignKey("group_groups.id"), nullable=False),
        sa.Column(
            "credit_user_id", sa.String(36), sa.ForeignKey("user_accounts.id"), nullable=False
        ),
        sa.Column(
            "debit_user_id", sa.String(36), sa.ForeignKey("user_accounts.id"), nullable=False
        ),
        sa.Column("amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("reason", sa.String(100), nullable=False),
        sa.CheckConstraint("credit_user_id <> debit_user_id"),
        *timestamps(),
    )
    op.create_index("ix_ledger_journal_group_id", "ledger_journal", ["group_id"])
    # Opening balances preserve existing installations without inventing past history.
    op.execute("""INSERT INTO ledger_journal
        (id, group_id, credit_user_id, debit_user_id, amount, reason)
        SELECT id, group_id, creditor_id, debtor_id, net_amount, 'opening-balance'
        FROM ledger_balances WHERE net_amount <> 0""")
    op.create_table(
        "notification_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("group_id", sa.String(36), sa.ForeignKey("group_groups.id"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("user_accounts.id"), nullable=False),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "available_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        *timestamps(),
    )
    op.create_index(
        "ix_notification_jobs_pending", "notification_jobs", ["completed_at", "available_at"]
    )
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "job_id",
            sa.String(36),
            sa.ForeignKey("notification_jobs.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("group_id", sa.String(36), sa.ForeignKey("group_groups.id"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("user_accounts.id"), nullable=False),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        *timestamps(),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.execute("""CREATE FUNCTION reject_financial_mutation() RETURNS trigger AS $$
        BEGIN RAISE EXCEPTION 'Financial records are immutable; append a reversal'; END;
        $$ LANGUAGE plpgsql""")
    for table in ("ledger_journal", "ledger_settlements"):
        op.execute(
            f"CREATE TRIGGER immutable_{table} BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION reject_financial_mutation()"
        )
        op.execute(
            f"CREATE TRIGGER immutable_truncate_{table} BEFORE TRUNCATE ON {table} "
            "FOR EACH STATEMENT EXECUTE FUNCTION reject_financial_mutation()"
        )


def downgrade():
    for table in ("ledger_journal", "ledger_settlements"):
        op.execute(f"DROP TRIGGER immutable_{table} ON {table}")
        op.execute(f"DROP TRIGGER immutable_truncate_{table} ON {table}")
    op.execute("DROP FUNCTION reject_financial_mutation()")
    op.drop_table("notifications")
    op.drop_table("notification_jobs")
    op.drop_table("ledger_journal")
    op.drop_constraint("uq_settlement_reversal", "ledger_settlements")
    op.drop_constraint("uq_settlement_retry", "ledger_settlements")
    op.drop_constraint("fk_settlement_reversal", "ledger_settlements")
    for column in ("reversal_of", "request_hash", "idempotency_key"):
        op.drop_column("ledger_settlements", column)
    op.drop_table("ledger_state")
