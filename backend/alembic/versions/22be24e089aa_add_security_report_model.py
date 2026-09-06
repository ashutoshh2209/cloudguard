"""Add SecurityReport model

Revision ID: 22be24e089aa
Revises: 11be24e089a9
Create Date: 2026-09-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '22be24e089aa'
down_revision: Union[str, None] = '11be24e089a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('security_reports',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('scan_id', sa.String(), nullable=False),
    sa.Column('report_type', sa.String(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('security_score', sa.Integer(), nullable=True),
    sa.Column('security_rating', sa.String(), nullable=True),
    sa.Column('finding_count', sa.Integer(), nullable=True),
    sa.Column('critical_count', sa.Integer(), nullable=True),
    sa.Column('high_count', sa.Integer(), nullable=True),
    sa.Column('medium_count', sa.Integer(), nullable=True),
    sa.Column('low_count', sa.Integer(), nullable=True),
    sa.Column('info_count', sa.Integer(), nullable=True),
    sa.Column('resource_count', sa.Integer(), nullable=True),
    sa.Column('coverage_percentage', sa.Integer(), nullable=True),
    sa.Column('generated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['scan_id'], ['scans.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_security_reports_scan_id'), 'security_reports', ['scan_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_security_reports_scan_id'), table_name='security_reports')
    op.drop_table('security_reports')
