"""add rfid_readings table

Revision ID: a3b7c9d2e4f6
Revises: c71886ab6a18
Create Date: 2026-06-23 16:40:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic
revision: str = 'a3b7c9d2e4f6'
down_revision: Union[str, None] = 'c71886ab6a18'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'rfid_readings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('attendance_sessions.id'), nullable=False),
        sa.Column('tag_hex_id', sa.String(200), nullable=False),
        sa.Column('tag_label', sa.String(50), nullable=True),
        sa.Column('seat_label', sa.String(20), nullable=True),
        sa.Column('angle_deg', sa.Float(), nullable=True),
        sa.Column('step_position', sa.Integer(), nullable=True),
        sa.Column('direction', sa.String(10), nullable=True),
        sa.Column('quadrant', sa.String(10), nullable=True),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_rfid_readings_session', 'rfid_readings', ['session_id'])
    op.create_index('ix_rfid_readings_tag', 'rfid_readings', ['tag_hex_id'])
    op.create_index('ix_rfid_readings_timestamp', 'rfid_readings', ['detected_at'])


def downgrade() -> None:
    op.drop_index('ix_rfid_readings_timestamp', table_name='rfid_readings')
    op.drop_index('ix_rfid_readings_tag', table_name='rfid_readings')
    op.drop_index('ix_rfid_readings_session', table_name='rfid_readings')
    op.drop_table('rfid_readings')
