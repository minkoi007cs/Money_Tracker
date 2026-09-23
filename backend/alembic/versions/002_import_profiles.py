"""Saved import mapping profiles.

Revision ID: 002_import_profiles
Revises: 001_initial
"""
from alembic import op
import sqlalchemy as sa

revision = "002_import_profiles"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "import_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("headers_hash", sa.String(64), nullable=False),
        sa.Column("mapping_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "headers_hash", name="uq_profile_user_headers"),
    )
    op.create_index("ix_import_profiles_user_id", "import_profiles", ["user_id"])


def downgrade():
    op.drop_index("ix_import_profiles_user_id", table_name="import_profiles")
    op.drop_table("import_profiles")
