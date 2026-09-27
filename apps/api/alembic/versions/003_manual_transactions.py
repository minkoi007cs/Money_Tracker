"""Allow transactions entered directly in the app.

Revision ID: 003_manual_transactions
Revises: 002_import_profiles
"""
from alembic import op
import sqlalchemy as sa

revision = "003_manual_transactions"
down_revision = "002_import_profiles"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("transactions") as batch:
        batch.alter_column("import_id", existing_type=sa.String(36), nullable=True)


def downgrade():
    op.execute("DELETE FROM transactions WHERE import_id IS NULL")
    with op.batch_alter_table("transactions") as batch:
        batch.alter_column("import_id", existing_type=sa.String(36), nullable=False)
