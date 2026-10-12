"""Add workspace and fields to findings

Revision ID: 88be24e089b0
Revises: 77be24e089af
Create Date: 2026-10-12 04:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '88be24e089b0'
down_revision: Union[str, None] = '77be24e089af'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('findings') as batch_op:
        batch_op.add_column(sa.Column('workspace_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('service', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('region', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()))
        batch_op.create_index(batch_op.f('ix_findings_workspace_id'), ['workspace_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_findings_service'), ['service'], unique=False)
        batch_op.create_index(batch_op.f('ix_findings_region'), ['region'], unique=False)
        batch_op.create_foreign_key(
            'fk_findings_workspace_id_workspaces',
            'workspaces',
            ['workspace_id'],
            ['id'],
            ondelete='CASCADE'
        )


def downgrade() -> None:
    with op.batch_alter_table('findings') as batch_op:
        batch_op.drop_constraint('fk_findings_workspace_id_workspaces', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_findings_region'))
        batch_op.drop_index(batch_op.f('ix_findings_service'))
        batch_op.drop_index(batch_op.f('ix_findings_workspace_id'))
        batch_op.drop_column('created_at')
        batch_op.drop_column('region')
        batch_op.drop_column('service')
        batch_op.drop_column('workspace_id')
