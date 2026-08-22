"""add_safety_infrastructure_tables

Revision ID: c21b22b894db
Revises: 12705d5f0498
Create Date: 2026-08-22 19:40:33.804239

"""
from alembic import op
import sqlalchemy as sa
import geoalchemy2


# revision identifiers, used by Alembic.
revision = 'c21b22b894db'
down_revision = '12705d5f0498'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Police Stations Table
    op.create_table(
        'police_stations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('osm_id', sa.Numeric(), nullable=True),
        sa.Column('name', sa.String(length=250), nullable=False),
        sa.Column('geom', geoalchemy2.types.Geometry(geometry_type='POINT', srid=4326, from_text='ST_GeomFromEWKT', name='geometry', spatial_index=False), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_police_stations_osm_id'), 'police_stations', ['osm_id'], unique=True)
    op.create_index('idx_police_stations_geom', 'police_stations', ['geom'], unique=False, postgresql_using='gist')

    # 2. Fire Stations Table
    op.create_table(
        'fire_stations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('osm_id', sa.Numeric(), nullable=True),
        sa.Column('name', sa.String(length=250), nullable=False),
        sa.Column('geom', geoalchemy2.types.Geometry(geometry_type='POINT', srid=4326, from_text='ST_GeomFromEWKT', name='geometry', spatial_index=False), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_fire_stations_osm_id'), 'fire_stations', ['osm_id'], unique=True)
    op.create_index('idx_fire_stations_geom', 'fire_stations', ['geom'], unique=False, postgresql_using='gist')


def downgrade() -> None:
    op.drop_index('idx_fire_stations_geom', table_name='fire_stations')
    op.drop_index(op.f('ix_fire_stations_osm_id'), table_name='fire_stations')
    op.drop_table('fire_stations')

    op.drop_index('idx_police_stations_geom', table_name='police_stations')
    op.drop_index(op.f('ix_police_stations_osm_id'), table_name='police_stations')
    op.drop_table('police_stations')

