"""add_admin_role_to_enum

Revision ID: ff9c5ec99136
Revises: f8e818695b6b
Create Date: 2026-04-10 10:07:31.233756
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision: str = 'ff9c5ec99136'
down_revision: Union[str, None] = 'f8e818695b6b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use execute to alter the enum type
    op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'admin';")


def downgrade() -> None:
    # Postgres doesn't easily support dropping enum values without recreating the type and rewriting data.
    # We will leave the value in place for downgrade to be safe.
    pass
