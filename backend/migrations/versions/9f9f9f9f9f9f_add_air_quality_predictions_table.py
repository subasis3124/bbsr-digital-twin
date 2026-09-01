"""add_air_quality_predictions_table

Revision ID: 9f9f9f9f9f9f
Revises: 81241eca7953
Create Date: 2026-09-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import geoalchemy2
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '9f9f9f9f9f9f'
down_revision = '81241eca7953'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create air_quality_predictions table
    op.create_table(
        'air_quality_predictions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('station_name', sa.String(length=100), nullable=False),
        sa.Column('pollutant', sa.String(length=20), nullable=False),
        sa.Column('forecast_issue_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('target_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('horizon_hours', sa.Integer(), nullable=False),
        sa.Column('predicted_value', sa.Numeric(), nullable=False),
        sa.Column('aqi_sub_index', sa.Integer(), nullable=True),
        sa.Column('model_name', sa.String(length=100), nullable=False),
        sa.Column('model_version', sa.String(length=50), nullable=False),
        sa.Column('geom', geoalchemy2.types.Geometry(geometry_type='POINT', srid=4326, spatial_index=False), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('data_provenance_status', sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    # Add indexes
    op.create_index(op.f('ix_air_quality_predictions_id'), 'air_quality_predictions', ['id'], unique=False)
    op.create_index(op.f('ix_air_quality_predictions_station_name'), 'air_quality_predictions', ['station_name'], unique=False)
    op.create_index(op.f('ix_air_quality_predictions_pollutant'), 'air_quality_predictions', ['pollutant'], unique=False)
    op.create_index(op.f('ix_air_quality_predictions_forecast_issue_time'), 'air_quality_predictions', ['forecast_issue_time'], unique=False)
    op.create_index(op.f('ix_air_quality_predictions_target_time'), 'air_quality_predictions', ['target_time'], unique=False)
    op.create_index(op.f('ix_air_quality_predictions_horizon_hours'), 'air_quality_predictions', ['horizon_hours'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_air_quality_predictions_horizon_hours'), table_name='air_quality_predictions')
    op.drop_index(op.f('ix_air_quality_predictions_target_time'), table_name='air_quality_predictions')
    op.drop_index(op.f('ix_air_quality_predictions_forecast_issue_time'), table_name='air_quality_predictions')
    op.drop_index(op.f('ix_air_quality_predictions_pollutant'), table_name='air_quality_predictions')
    op.drop_index(op.f('ix_air_quality_predictions_station_name'), table_name='air_quality_predictions')
    op.drop_index(op.f('ix_air_quality_predictions_id'), table_name='air_quality_predictions')
    # Drop table
    op.drop_table('air_quality_predictions')
