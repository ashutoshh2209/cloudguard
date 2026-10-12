"""Update AWS connections with workspace_id and external_id

Revision ID: 55be24e089ad
Revises: 44be24e089ac
Create Date: 2026-10-12 03:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '55be24e089ad'
down_revision: Union[str, None] = '44be24e089ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('aws_connections') as batch_op:
        batch_op.add_column(sa.Column('workspace_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('external_id', sa.String(), nullable=True))
        batch_op.create_index(batch_op.f('ix_aws_connections_workspace_id'), ['workspace_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_aws_connections_workspace_id_workspaces',
            'workspaces',
            ['workspace_id'],
            ['id'],
            ondelete='CASCADE'
        )


def downgrade() -> None:
    with op.batch_alter_table('aws_connections') as batch_op:
        batch_op.drop_constraint('fk_aws_connections_workspace_id_workspaces', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_aws_connections_workspace_id'))
        batch_op.drop_column('external_id')
        batch_op.drop_column('workspace_id')
