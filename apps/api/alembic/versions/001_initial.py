"""Initial application tables.

Revision ID: 001_initial
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table(
        "user_settings",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
    )
    op.create_table(
        "import_batches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("imported_count", sa.Integer(), nullable=False),
        sa.Column("duplicate_count", sa.Integer(), nullable=False),
        sa.Column("rejected_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_import_batches_user_id", "import_batches", ["user_id"])
    op.create_table(
        "transactions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("import_id", sa.String(36), sa.ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("description_raw", sa.Text(), nullable=False),
        sa.Column("description_normalized", sa.Text(), nullable=False),
        sa.Column("merchant_name", sa.String(255), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("category_source", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Numeric(3, 2), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("is_transfer", sa.Boolean(), nullable=False),
        sa.Column("is_refund", sa.Boolean(), nullable=False),
        sa.Column("is_subscription", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "fingerprint", name="uq_user_fingerprint"),
    )
    op.create_index("ix_transactions_import_id", "transactions", ["import_id"])
    op.create_index("ix_transaction_user_date", "transactions", ["user_id", "transaction_date"])
    op.create_index("ix_transaction_user_merchant", "transactions", ["user_id", "merchant_name"])
    op.create_table(
        "merchant_category_preferences",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("merchant_key", sa.String(255), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.UniqueConstraint("user_id", "merchant_key", name="uq_preference_user_merchant"),
    )
    op.create_index("ix_merchant_category_preferences_user_id", "merchant_category_preferences", ["user_id"])
    op.create_table(
        "recurring_overrides",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("merchant_key", sa.String(255), nullable=False),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.UniqueConstraint("user_id", "merchant_key", name="uq_override_user_merchant"),
    )
    op.create_index("ix_recurring_overrides_user_id", "recurring_overrides", ["user_id"])


def downgrade():
    op.drop_index("ix_recurring_overrides_user_id", table_name="recurring_overrides")
    op.drop_table("recurring_overrides")
    op.drop_index("ix_merchant_category_preferences_user_id", table_name="merchant_category_preferences")
    op.drop_table("merchant_category_preferences")
    op.drop_index("ix_transaction_user_merchant", table_name="transactions")
    op.drop_index("ix_transaction_user_date", table_name="transactions")
    op.drop_index("ix_transactions_import_id", table_name="transactions")
    op.drop_table("transactions")
    op.drop_index("ix_import_batches_user_id", table_name="import_batches")
    op.drop_table("import_batches")
    op.drop_table("user_settings")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
