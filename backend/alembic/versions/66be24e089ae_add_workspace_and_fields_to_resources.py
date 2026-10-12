"""Add workspace_id and fields to resources

Revision ID: 66be24e089ae
Revises: 55be24e089ad
Create Date: 2026-10-12 03:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '66be24e089ae'
down_revision: Union[str, None] = '55be24e089ad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('resources') as batch_op:
        batch_op.add_column(sa.Column('workspace_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('resource_name', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('arn', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.alter_column('scan_id', existing_type=sa.String(), nullable=True)
        batch_op.create_index(batch_op.f('ix_resources_workspace_id'), ['workspace_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_resources_arn'), ['arn'], unique=False)
        batch_op.create_foreign_key(
            'fk_resources_workspace_id_workspaces',
            'workspaces',
            ['workspace_id'],
            ['id'],
            ondelete='CASCADE'
        )


def downgrade() -> None:
    with op.batch_alter_table('resources') as batch_op:
        batch_op.drop_constraint('fk_resources_workspace_id_workspaces', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_resources_arn'))
        batch_op.drop_index(batch_op.f('ix_resources_workspace_id'))
        batch_op.alter_column('scan_id', existing_type=sa.String(), nullable=False)
        batch_op.drop_column('updated_at')
        batch_op.drop_column('arn')
        batch_op.drop_column('resource_name')
        batch_op.drop_column('workspace_id')
