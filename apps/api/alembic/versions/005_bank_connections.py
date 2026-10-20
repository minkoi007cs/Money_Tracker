"""Plaid bank connections, encrypted credentials, balances, transaction identity.

Revision ID: 005_bank_connections
Revises: 004_bank_accounts
"""
from alembic import op
import sqlalchemy as sa

revision = "005_bank_connections"
down_revision = "004_bank_accounts"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "bank_connections",
        sa.UniqueConstraint("user_id", "institution_id", "environment", name="uq_bank_user_institution_environment"),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", sa.String(255), unique=True, nullable=False),
        sa.Column("access_token_encrypted", sa.Text(), nullable=True),
        sa.Column("environment", sa.String(20), nullable=False),
        sa.Column("institution_name", sa.String(100), nullable=False),
        sa.Column("institution_id", sa.String(100), nullable=False),
        sa.Column("cursor", sa.Text(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("history_ready", sa.Boolean(), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sync_lock_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_bank_connections_user_id", "bank_connections", ["user_id"])
    with op.batch_alter_table("accounts") as batch:
        batch.add_column(sa.Column("bank_connection_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("external_account_id", sa.String(255), nullable=True))
        batch.add_column(sa.Column("account_type", sa.String(30), nullable=True))
        batch.add_column(sa.Column("mask", sa.String(10), nullable=True))
        batch.add_column(sa.Column("bank_balance", sa.Numeric(18, 2), nullable=True))
        batch.add_column(sa.Column("available_balance", sa.Numeric(18, 2), nullable=True))
        batch.add_column(sa.Column("balance_fetched_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_foreign_key("fk_accounts_bank_connection", "bank_connections", ["bank_connection_id"], ["id"], ondelete="SET NULL")
        batch.create_unique_constraint("uq_accounts_external_id", ["external_account_id"])
        batch.create_index("ix_accounts_bank_connection_id", ["bank_connection_id"])
    with op.batch_alter_table("transactions") as batch:
        batch.add_column(sa.Column("bank_connection_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("external_transaction_id", sa.String(255), nullable=True))
        batch.add_column(sa.Column("pending", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("bank_overrides", sa.Text(), nullable=False, server_default="[]"))
        batch.create_foreign_key("fk_transactions_bank_connection", "bank_connections", ["bank_connection_id"], ["id"], ondelete="SET NULL")
        batch.create_unique_constraint("uq_transactions_external_id", ["external_transaction_id"])
        batch.create_index("ix_transactions_bank_connection_id", ["bank_connection_id"])


def downgrade():
    with op.batch_alter_table("transactions") as batch:
        batch.drop_index("ix_transactions_bank_connection_id")
        batch.drop_constraint("fk_transactions_bank_connection", type_="foreignkey")
        batch.drop_constraint("uq_transactions_external_id", type_="unique")
        for column in ["bank_overrides", "pending", "external_transaction_id", "bank_connection_id"]:
            batch.drop_column(column)
    with op.batch_alter_table("accounts") as batch:
        batch.drop_index("ix_accounts_bank_connection_id")
        batch.drop_constraint("fk_accounts_bank_connection", type_="foreignkey")
        batch.drop_constraint("uq_accounts_external_id", type_="unique")
        for column in ["balance_fetched_at", "available_balance", "bank_balance", "mask", "account_type", "external_account_id", "bank_connection_id"]:
            batch.drop_column(column)
    op.drop_index("ix_bank_connections_user_id", table_name="bank_connections")
    op.drop_table("bank_connections")
