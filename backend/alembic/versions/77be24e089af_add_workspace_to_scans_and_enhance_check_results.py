"""Add workspace to scans and enhance check results

Revision ID: 77be24e089af
Revises: 66be24e089ae
Create Date: 2026-10-12 03:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '77be24e089af'
down_revision: Union[str, None] = '66be24e089ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update scans table
    with op.batch_alter_table('scans') as batch_op:
        batch_op.add_column(sa.Column('workspace_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('checks_passed', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('checks_errored', sa.Integer(), nullable=True, server_default='0'))
        batch_op.alter_column('aws_connection_id', existing_type=sa.String(), nullable=True)
        batch_op.create_index(batch_op.f('ix_scans_workspace_id'), ['workspace_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_scans_workspace_id_workspaces',
            'workspaces',
            ['workspace_id'],
            ['id'],
            ondelete='CASCADE'
        )

    # 2. Update check_results table
    with op.batch_alter_table('check_results') as batch_op:
        batch_op.add_column(sa.Column('message', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('recommendation', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('evidence', sa.JSON().with_variant(postgresql.JSONB, 'postgresql'), nullable=True))
        batch_op.create_index(batch_op.f('ix_check_results_rule_id'), ['rule_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_check_results_status'), ['status'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('check_results') as batch_op:
        batch_op.drop_index(batch_op.f('ix_check_results_status'))
        batch_op.drop_index(batch_op.f('ix_check_results_rule_id'))
        batch_op.drop_column('evidence')
        batch_op.drop_column('recommendation')
        batch_op.drop_column('message')

    with op.batch_alter_table('scans') as batch_op:
        batch_op.drop_constraint('fk_scans_workspace_id_workspaces', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_scans_workspace_id'))
        batch_op.drop_column('checks_errored')
        batch_op.drop_column('checks_passed')
        batch_op.drop_column('workspace_id')
