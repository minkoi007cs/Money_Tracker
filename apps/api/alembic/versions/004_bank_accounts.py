"""Bank accounts and account ownership for transactions.

Revision ID: 004_bank_accounts
Revises: 003_manual_transactions
"""
from alembic import op
import sqlalchemy as sa

revision = "004_bank_accounts"
down_revision = "003_manual_transactions"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "accounts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("opening_balance", sa.Numeric(18, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_accounts_user_id", "accounts", ["user_id"])
    with op.batch_alter_table("transactions") as batch:
        batch.add_column(sa.Column("account_id", sa.String(36), nullable=True))
        batch.create_foreign_key("fk_transactions_account_id", "accounts", ["account_id"], ["id"], ondelete="SET NULL")
        batch.create_index("ix_transactions_account_id", ["account_id"])


def downgrade():
    with op.batch_alter_table("transactions") as batch:
        batch.drop_index("ix_transactions_account_id")
        batch.drop_constraint("fk_transactions_account_id", type_="foreignkey")
        batch.drop_column("account_id")
    op.drop_index("ix_accounts_user_id", table_name="accounts")
    op.drop_table("accounts")
