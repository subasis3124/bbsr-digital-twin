"""add_city_state_snapshots_table

Revision ID: e11e11e11e11
Revises: d10a10a10a10
Create Date: 2026-09-02 02:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

# revision identifiers, used by Alembic.
revision = 'e11e11e11e11'
down_revision = 'd10a10a10a10'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create city_state_snapshots table
    op.create_table(
        'city_state_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('spatial_unit_type', sa.String(length=50), nullable=False, server_default='grid_cell'),
        sa.Column('spatial_id', sa.String(length=100), nullable=False),
        sa.Column('cell_id', sa.Integer(), nullable=True),
        sa.Column('ward_id', sa.Integer(), nullable=True),
        sa.Column('road_id', sa.Integer(), nullable=True),
        sa.Column('state_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('target_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('forecast_horizon_minutes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('state_type', sa.String(length=20), nullable=False, server_default='CURRENT'),
        sa.Column('flood_risk_probability', sa.Numeric(), nullable=True),
        sa.Column('flood_risk_level', sa.String(length=20), nullable=True),
        sa.Column('traffic_congestion_index', sa.Numeric(), nullable=True),
        sa.Column('aqi_value', sa.Integer(), nullable=True),
        sa.Column('air_quality_category', sa.String(length=50), nullable=True),
        sa.Column('population_count', sa.Integer(), nullable=True),
        sa.Column('population_density', sa.Numeric(), nullable=True),
        sa.Column('emergency_service_density', sa.Numeric(), nullable=True),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('data_provenance_status', sa.String(length=50), nullable=False, server_default='observed'),
        sa.Column('state_schema_version', sa.String(length=20), nullable=False, server_default='1.0.0'),
        sa.Column('geom', Geometry(geometry_type='GEOMETRY', srid=4326, spatial_index=False), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['cell_id'], ['spatial_grid_cells.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['ward_id'], ['wards.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['road_id'], ['roads.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    # 2. Add indexes
    op.create_index(op.f('ix_city_state_snapshots_id'), 'city_state_snapshots', ['id'], unique=False)
    op.create_index(op.f('ix_city_state_snapshots_spatial_unit_type'), 'city_state_snapshots', ['spatial_unit_type'], unique=False)
    op.create_index(op.f('ix_city_state_snapshots_spatial_id'), 'city_state_snapshots', ['spatial_id'], unique=False)
    op.create_index(op.f('ix_city_state_snapshots_cell_id'), 'city_state_snapshots', ['cell_id'], unique=False)
    op.create_index(op.f('ix_city_state_snapshots_ward_id'), 'city_state_snapshots', ['ward_id'], unique=False)
    op.create_index(op.f('ix_city_state_snapshots_road_id'), 'city_state_snapshots', ['road_id'], unique=False)
    op.create_index(op.f('ix_city_state_snapshots_state_timestamp'), 'city_state_snapshots', ['state_timestamp'], unique=False)
    op.create_index(op.f('ix_city_state_snapshots_target_timestamp'), 'city_state_snapshots', ['target_timestamp'], unique=False)
    op.create_index(op.f('ix_city_state_snapshots_forecast_horizon_minutes'), 'city_state_snapshots', ['forecast_horizon_minutes'], unique=False)
    op.create_index(op.f('ix_city_state_snapshots_state_type'), 'city_state_snapshots', ['state_type'], unique=False)


def downgrade() -> None:
    # 1. Drop indexes
    op.drop_index(op.f('ix_city_state_snapshots_state_type'), table_name='city_state_snapshots')
    op.drop_index(op.f('ix_city_state_snapshots_forecast_horizon_minutes'), table_name='city_state_snapshots')
    op.drop_index(op.f('ix_city_state_snapshots_target_timestamp'), table_name='city_state_snapshots')
    op.drop_index(op.f('ix_city_state_snapshots_state_timestamp'), table_name='city_state_snapshots')
    op.drop_index(op.f('ix_city_state_snapshots_road_id'), table_name='city_state_snapshots')
    op.drop_index(op.f('ix_city_state_snapshots_ward_id'), table_name='city_state_snapshots')
    op.drop_index(op.f('ix_city_state_snapshots_cell_id'), table_name='city_state_snapshots')
    op.drop_index(op.f('ix_city_state_snapshots_spatial_id'), table_name='city_state_snapshots')
    op.drop_index(op.f('ix_city_state_snapshots_spatial_unit_type'), table_name='city_state_snapshots')
    op.drop_index(op.f('ix_city_state_snapshots_id'), table_name='city_state_snapshots')
    # 2. Drop table
    op.drop_table('city_state_snapshots')
