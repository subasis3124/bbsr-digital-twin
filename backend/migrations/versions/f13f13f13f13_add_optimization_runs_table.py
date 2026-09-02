"""add_optimization_runs_table

Revision ID: f13f13f13f13
Revises: f12f12f12f12
Create Date: 2026-09-02 04:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f13f13f13f13'
down_revision = 'f12f12f12f12'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create optimization_runs table
    op.create_table(
        'optimization_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.String(length=36), nullable=False),
        sa.Column('scenario_id', sa.String(length=36), nullable=True),
        sa.Column('simulation_id', sa.String(length=36), nullable=True),
        sa.Column('base_state_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('optimization_timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('optimization_method', sa.String(length=50), nullable=False, server_default='ortools_min_cost_flow'),
        sa.Column('objective_function', sa.String(length=100), nullable=False, server_default='minimize_weighted_travel_cost'),
        sa.Column('engine_version', sa.String(length=20), nullable=False, server_default='1.0.0'),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('constraints', sa.JSON(), nullable=False),
        sa.Column('resource_types', sa.JSON(), nullable=False),
        sa.Column('total_demand', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('served_demand', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('unserved_demand', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_travel_cost', sa.Numeric(), nullable=False, server_default='0.0'),
        sa.Column('average_travel_cost', sa.Numeric(), nullable=False, server_default='0.0'),
        sa.Column('demand_summary', sa.JSON(), nullable=False),
        sa.Column('resource_summary', sa.JSON(), nullable=False),
        sa.Column('allocation_results', sa.JSON(), nullable=False),
        sa.Column('baseline_results', sa.JSON(), nullable=False),
        sa.Column('impact_comparison', sa.JSON(), nullable=True),
        sa.Column('provenance', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_optimization_runs_id'), 'optimization_runs', ['id'], unique=False)
    op.create_index(op.f('ix_optimization_runs_run_id'), 'optimization_runs', ['run_id'], unique=True)
    op.create_index(op.f('ix_optimization_runs_scenario_id'), 'optimization_runs', ['scenario_id'], unique=False)
    op.create_index(op.f('ix_optimization_runs_simulation_id'), 'optimization_runs', ['simulation_id'], unique=False)
    op.create_index(op.f('ix_optimization_runs_base_state_timestamp'), 'optimization_runs', ['base_state_timestamp'], unique=False)
    op.create_index(op.f('ix_optimization_runs_optimization_timestamp'), 'optimization_runs', ['optimization_timestamp'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_optimization_runs_optimization_timestamp'), table_name='optimization_runs')
    op.drop_index(op.f('ix_optimization_runs_base_state_timestamp'), table_name='optimization_runs')
    op.drop_index(op.f('ix_optimization_runs_simulation_id'), table_name='optimization_runs')
    op.drop_index(op.f('ix_optimization_runs_scenario_id'), table_name='optimization_runs')
    op.drop_index(op.f('ix_optimization_runs_run_id'), table_name='optimization_runs')
    op.drop_index(op.f('ix_optimization_runs_id'), table_name='optimization_runs')
    op.drop_table('optimization_runs')
