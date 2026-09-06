"""initial_migration

Revision ID: 11be24e089a9
Revises: 
Create Date: 2026-09-06 17:43:57.636737

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '11be24e089a9'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. AWS Connections
    op.create_table(
        'aws_connections',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('account_id', sa.String(), nullable=False),
        sa.Column('role_arn', sa.String(), nullable=False),
        sa.Column('region', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_aws_connections_account_id'), 'aws_connections', ['account_id'], unique=True)

    # 2. Scans
    op.create_table(
        'scans',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('aws_connection_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resources_scanned', sa.Integer(), nullable=True),
        sa.Column('checks_attempted', sa.Integer(), nullable=True),
        sa.Column('checks_completed', sa.Integer(), nullable=True),
        sa.Column('checks_failed', sa.Integer(), nullable=True),
        sa.Column('coverage_percentage', sa.Integer(), nullable=True),
        sa.Column('security_score', sa.Integer(), nullable=True),
        sa.Column('security_rating', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['aws_connection_id'], ['aws_connections.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_scans_aws_connection_id'), 'scans', ['aws_connection_id'], unique=False)
    op.create_index(op.f('ix_scans_status'), 'scans', ['status'], unique=False)
    op.create_index(op.f('ix_scans_created_at'), 'scans', ['created_at'], unique=False)

    # 3. Resources
    op.create_table(
        'resources',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('scan_id', sa.String(), nullable=False),
        sa.Column('aws_connection_id', sa.String(), nullable=False),
        sa.Column('resource_id', sa.String(), nullable=False),
        sa.Column('resource_type', sa.String(), nullable=False),
        sa.Column('service', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('region', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('discovered_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['aws_connection_id'], ['aws_connections.id'], ),
        sa.ForeignKeyConstraint(['scan_id'], ['scans.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_resources_scan_id'), 'resources', ['scan_id'], unique=False)
    op.create_index(op.f('ix_resources_resource_type'), 'resources', ['resource_type'], unique=False)
    op.create_index(op.f('ix_resources_service'), 'resources', ['service'], unique=False)
    op.create_index(op.f('ix_resources_region'), 'resources', ['region'], unique=False)

    # 4. Findings
    op.create_table(
        'findings',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('scan_id', sa.String(), nullable=False),
        sa.Column('resource_id', sa.String(), nullable=False),
        sa.Column('rule_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('severity', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('risk_score', sa.Integer(), nullable=True),
        sa.Column('priority', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('recommendation', sa.String(), nullable=True),
        sa.Column('evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('risk_factors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['scan_id'], ['scans.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_findings_scan_id'), 'findings', ['scan_id'], unique=False)
    op.create_index(op.f('ix_findings_rule_id'), 'findings', ['rule_id'], unique=False)
    op.create_index(op.f('ix_findings_severity'), 'findings', ['severity'], unique=False)
    op.create_index(op.f('ix_findings_category'), 'findings', ['category'], unique=False)
    op.create_index(op.f('ix_findings_risk_score'), 'findings', ['risk_score'], unique=False)
    op.create_index(op.f('ix_findings_status'), 'findings', ['status'], unique=False)

    # 5. Check Results
    op.create_table(
        'check_results',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('scan_id', sa.String(), nullable=False),
        sa.Column('resource_id', sa.String(), nullable=False),
        sa.Column('rule_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('checked_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['scan_id'], ['scans.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_check_results_scan_id'), 'check_results', ['scan_id'], unique=False)

    # 6. Category Scores
    op.create_table(
        'category_scores',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('scan_id', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('finding_count', sa.Integer(), nullable=True),
        sa.Column('critical_count', sa.Integer(), nullable=True),
        sa.Column('high_count', sa.Integer(), nullable=True),
        sa.Column('medium_count', sa.Integer(), nullable=True),
        sa.Column('low_count', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['scan_id'], ['scans.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_category_scores_scan_id'), 'category_scores', ['scan_id'], unique=False)


def downgrade() -> None:
    op.drop_table('category_scores')
    op.drop_table('check_results')
    op.drop_table('findings')
    op.drop_table('resources')
    op.drop_table('scans')
    op.drop_table('aws_connections')
