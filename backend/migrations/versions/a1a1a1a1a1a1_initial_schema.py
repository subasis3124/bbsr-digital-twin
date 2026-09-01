"""initial schema

Revision ID: a1a1a1a1a1a1
Revises: 
Create Date: 2026-08-17 01:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
import geoalchemy2

# revision identifiers, used by Alembic.
revision = 'a1a1a1a1a1a1'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Enable PostGIS Extension (if permitted)
    try:
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    except Exception as e:
        print(f"Skipping CREATE EXTENSION postgis: {e}")

    # 2. City Table
    op.create_table(
        'city',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('geom', geoalchemy2.types.Geometry(geometry_type='POLYGON', srid=4326, from_text='ST_GeomFromEWKT', name='geometry', spatial_index=False), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_city_geom', 'city', ['geom'], unique=False, postgresql_using='gist')

    # 3. Wards Table
    op.create_table(
        'wards',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ward_number', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=True),
        sa.Column('population_est', sa.Integer(), nullable=True),
        sa.Column('geom', geoalchemy2.types.Geometry(geometry_type='MULTIPOLYGON', srid=4326, from_text='ST_GeomFromEWKT', name='geometry', spatial_index=False), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_wards_ward_number'), 'wards', ['ward_number'], unique=True)
    op.create_index('idx_wards_geom', 'wards', ['geom'], unique=False, postgresql_using='gist')

    # 4. Roads Table
    op.create_table(
        'roads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('osm_id', sa.Numeric(), nullable=True),
        sa.Column('name', sa.String(length=200), nullable=True),
        sa.Column('highway_type', sa.String(length=50), nullable=True),
        sa.Column('lanes', sa.Integer(), nullable=True),
        sa.Column('maxspeed', sa.Integer(), nullable=True),
        sa.Column('oneway', sa.Boolean(), nullable=True),
        sa.Column('geom', geoalchemy2.types.Geometry(geometry_type='LINESTRING', srid=4326, from_text='ST_GeomFromEWKT', name='geometry', spatial_index=False), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_roads_osm_id'), 'roads', ['osm_id'], unique=True)
    op.create_index('idx_roads_geom', 'roads', ['geom'], unique=False, postgresql_using='gist')

    # 5. Buildings Table
    op.create_table(
        'buildings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('osm_id', sa.Numeric(), nullable=True),
        sa.Column('building_type', sa.String(length=100), nullable=True),
        sa.Column('height', sa.Numeric(), nullable=True),
        sa.Column('levels', sa.Integer(), nullable=True),
        sa.Column('geom', geoalchemy2.types.Geometry(geometry_type='POLYGON', srid=4326, from_text='ST_GeomFromEWKT', name='geometry', spatial_index=False), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_buildings_osm_id'), 'buildings', ['osm_id'], unique=True)
    op.create_index('idx_buildings_geom', 'buildings', ['geom'], unique=False, postgresql_using='gist')

    # 6. Hospitals Table
    op.create_table(
        'hospitals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('osm_id', sa.Numeric(), nullable=True),
        sa.Column('name', sa.String(length=250), nullable=False),
        sa.Column('beds', sa.Integer(), nullable=True),
        sa.Column('geom', geoalchemy2.types.Geometry(geometry_type='POINT', srid=4326, from_text='ST_GeomFromEWKT', name='geometry', spatial_index=False), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_hospitals_osm_id'), 'hospitals', ['osm_id'], unique=True)
    op.create_index('idx_hospitals_geom', 'hospitals', ['geom'], unique=False, postgresql_using='gist')

    # 7. Schools Table
    op.create_table(
        'schools',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('osm_id', sa.Numeric(), nullable=True),
        sa.Column('name', sa.String(length=250), nullable=False),
        sa.Column('geom', geoalchemy2.types.Geometry(geometry_type='POINT', srid=4326, from_text='ST_GeomFromEWKT', name='geometry', spatial_index=False), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_schools_osm_id'), 'schools', ['osm_id'], unique=True)
    op.create_index('idx_schools_geom', 'schools', ['geom'], unique=False, postgresql_using='gist')

    # 8. Bus Stops Table
    op.create_table(
        'bus_stops',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('osm_id', sa.Numeric(), nullable=True),
        sa.Column('name', sa.String(length=250), nullable=True),
        sa.Column('geom', geoalchemy2.types.Geometry(geometry_type='POINT', srid=4326, from_text='ST_GeomFromEWKT', name='geometry', spatial_index=False), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bus_stops_osm_id'), 'bus_stops', ['osm_id'], unique=True)
    op.create_index('idx_bus_stops_geom', 'bus_stops', ['geom'], unique=False, postgresql_using='gist')

    # 9. Bus Routes Table
    op.create_table(
        'bus_routes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('route_name', sa.String(length=100), nullable=False),
        sa.Column('operator', sa.String(length=100), nullable=True),
        sa.Column('geom', geoalchemy2.types.Geometry(geometry_type='LINESTRING', srid=4326, from_text='ST_GeomFromEWKT', name='geometry', spatial_index=False), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_bus_routes_geom', 'bus_routes', ['geom'], unique=False, postgresql_using='gist')

    # 10. Water Bodies Table
    op.create_table(
        'water_bodies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('osm_id', sa.Numeric(), nullable=True),
        sa.Column('name', sa.String(length=150), nullable=True),
        sa.Column('water_type', sa.String(length=50), nullable=True),
        sa.Column('geom', geoalchemy2.types.Geometry(geometry_type='POLYGON', srid=4326, from_text='ST_GeomFromEWKT', name='geometry', spatial_index=False), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_water_bodies_osm_id'), 'water_bodies', ['osm_id'], unique=True)
    op.create_index('idx_water_bodies_geom', 'water_bodies', ['geom'], unique=False, postgresql_using='gist')

    # 11. Weather Table
    op.create_table(
        'weather',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('temperature', sa.Numeric(), nullable=True),
        sa.Column('rainfall', sa.Numeric(), nullable=True),
        sa.Column('humidity', sa.Numeric(), nullable=True),
        sa.Column('wind_speed', sa.Numeric(), nullable=True),
        sa.Column('is_forecast', sa.Boolean(), nullable=True),
        sa.Column('source', sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_weather_timestamp'), 'weather', ['timestamp'], unique=False)

    # 12. Air Quality Table
    op.create_table(
        'air_quality',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('station_name', sa.String(length=100), nullable=False),
        sa.Column('pm25', sa.Numeric(), nullable=True),
        sa.Column('pm10', sa.Numeric(), nullable=True),
        sa.Column('co', sa.Numeric(), nullable=True),
        sa.Column('no2', sa.Numeric(), nullable=True),
        sa.Column('so2', sa.Numeric(), nullable=True),
        sa.Column('o3', sa.Numeric(), nullable=True),
        sa.Column('aqi_value', sa.Integer(), nullable=True),
        sa.Column('geom', geoalchemy2.types.Geometry(geometry_type='POINT', srid=4326, from_text='ST_GeomFromEWKT', name='geometry', spatial_index=False), nullable=False),
        sa.Column('source', sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_air_quality_timestamp'), 'air_quality', ['timestamp'], unique=False)
    op.create_index('idx_air_quality_geom', 'air_quality', ['geom'], unique=False, postgresql_using='gist')

    # 13. Traffic Table
    op.create_table(
        'traffic',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('road_id', sa.Integer(), nullable=False),
        sa.Column('observed_speed', sa.Integer(), nullable=False),
        sa.Column('congestion_ratio', sa.Numeric(), nullable=True),
        sa.Column('source', sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(['road_id'], ['roads.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_traffic_road_id'), 'traffic', ['road_id'], unique=False)
    op.create_index(op.f('ix_traffic_timestamp'), 'traffic', ['timestamp'], unique=False)

    # 14. Population Table
    op.create_table(
        'population',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('population_count', sa.Integer(), nullable=False),
        sa.Column('geom', geoalchemy2.types.Geometry(geometry_type='POLYGON', srid=4326, from_text='ST_GeomFromEWKT', name='geometry', spatial_index=False), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_population_geom', 'population', ['geom'], unique=False, postgresql_using='gist')

    # 15. Flood Events Table
    op.create_table(
        'flood_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_name', sa.String(length=150), nullable=True),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('severity', sa.String(length=50), nullable=True),
        sa.Column('geom', geoalchemy2.types.Geometry(geometry_type='MULTIPOLYGON', srid=4326, from_text='ST_GeomFromEWKT', name='geometry', spatial_index=False), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_flood_events_geom', 'flood_events', ['geom'], unique=False, postgresql_using='gist')

    # 16. Spatial Grid Cells Table
    op.create_table(
        'spatial_grid_cells',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cell_code', sa.String(length=50), nullable=False),
        sa.Column('geom', geoalchemy2.types.Geometry(geometry_type='POLYGON', srid=4326, from_text='ST_GeomFromEWKT', name='geometry', spatial_index=False), nullable=False),
        sa.Column('centroid', geoalchemy2.types.Geometry(geometry_type='POINT', srid=4326, from_text='ST_GeomFromEWKT', name='geometry', spatial_index=False), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_spatial_grid_cells_cell_code'), 'spatial_grid_cells', ['cell_code'], unique=True)
    op.create_index('idx_spatial_grid_cells_geom', 'spatial_grid_cells', ['geom'], unique=False, postgresql_using='gist')

    # 17. Satellite Features Table
    op.create_table(
        'satellite_features',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cell_id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('elevation', sa.Numeric(), nullable=True),
        sa.Column('slope', sa.Numeric(), nullable=True),
        sa.Column('ndvi', sa.Numeric(), nullable=True),
        sa.Column('ndwi', sa.Numeric(), nullable=True),
        sa.Column('ndbi', sa.Numeric(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['cell_id'], ['spatial_grid_cells.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_satellite_features_cell_id'), 'satellite_features', ['cell_id'], unique=False)
    op.create_index(op.f('ix_satellite_features_timestamp'), 'satellite_features', ['timestamp'], unique=False)

    # 18. Predictions Table
    op.create_table(
        'predictions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cell_id', sa.Integer(), nullable=False),
        sa.Column('model_name', sa.String(length=100), nullable=False),
        sa.Column('model_version', sa.String(length=50), nullable=False),
        sa.Column('prediction_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('predicted_probability', sa.Numeric(), nullable=False),
        sa.Column('predicted_class', sa.String(length=50), nullable=False),
        sa.Column('feature_importance_shap', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['cell_id'], ['spatial_grid_cells.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_predictions_cell_id'), 'predictions', ['cell_id'], unique=False)
    op.create_index(op.f('ix_predictions_prediction_time'), 'predictions', ['prediction_time'], unique=False)

    # 19. Simulations Table
    op.create_table(
        'simulations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('simulation_uuid', sa.String(length=36), nullable=False),
        sa.Column('scenario_name', sa.String(length=100), nullable=False),
        sa.Column('triggered_by', sa.String(length=100), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('cell_id', sa.Integer(), nullable=False),
        sa.Column('baseline_class', sa.String(length=50), nullable=False),
        sa.Column('simulated_class', sa.String(length=50), nullable=False),
        sa.Column('delta_risk', sa.Numeric(), nullable=False),
        sa.ForeignKeyConstraint(['cell_id'], ['spatial_grid_cells.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_simulations_cell_id'), 'simulations', ['cell_id'], unique=False)
    op.create_index(op.f('ix_simulations_simulation_uuid'), 'simulations', ['simulation_uuid'], unique=False)


def downgrade() -> None:
    # Drop simulations
    op.drop_index(op.f('ix_simulations_simulation_uuid'), table_name='simulations')
    op.drop_index(op.f('ix_simulations_cell_id'), table_name='simulations')
    op.drop_table('simulations')

    # Drop predictions
    op.drop_index(op.f('ix_predictions_prediction_time'), table_name='predictions')
    op.drop_index(op.f('ix_predictions_cell_id'), table_name='predictions')
    op.drop_table('predictions')

    # Drop satellite_features
    op.drop_index(op.f('ix_satellite_features_timestamp'), table_name='satellite_features')
    op.drop_index(op.f('ix_satellite_features_cell_id'), table_name='satellite_features')
    op.drop_table('satellite_features')

    # Drop spatial_grid_cells
    op.drop_index('idx_spatial_grid_cells_geom', table_name='spatial_grid_cells')
    op.drop_index(op.f('ix_spatial_grid_cells_cell_code'), table_name='spatial_grid_cells')
    op.drop_table('spatial_grid_cells')

    # Drop flood_events
    op.drop_index('idx_flood_events_geom', table_name='flood_events')
    op.drop_table('flood_events')

    # Drop population
    op.drop_index('idx_population_geom', table_name='population')
    op.drop_table('population')

    # Drop traffic
    op.drop_index(op.f('ix_traffic_timestamp'), table_name='traffic')
    op.drop_index(op.f('ix_traffic_road_id'), table_name='traffic')
    op.drop_table('traffic')

    # Drop air_quality
    op.drop_index('idx_air_quality_geom', table_name='air_quality')
    op.drop_index(op.f('ix_air_quality_timestamp'), table_name='air_quality')
    op.drop_table('air_quality')

    # Drop weather
    op.drop_index(op.f('ix_weather_timestamp'), table_name='weather')
    op.drop_table('weather')

    # Drop water_bodies
    op.drop_index('idx_water_bodies_geom', table_name='water_bodies')
    op.drop_index(op.f('ix_water_bodies_osm_id'), table_name='water_bodies')
    op.drop_table('water_bodies')

    # Drop bus_routes
    op.drop_index('idx_bus_routes_geom', table_name='bus_routes')
    op.drop_table('bus_routes')

    # Drop bus_stops
    op.drop_index('idx_bus_stops_geom', table_name='bus_stops')
    op.drop_index(op.f('ix_bus_stops_osm_id'), table_name='bus_stops')
    op.drop_table('bus_stops')

    # Drop schools
    op.drop_index('idx_schools_geom', table_name='schools')
    op.drop_index(op.f('ix_schools_osm_id'), table_name='schools')
    op.drop_table('schools')

    # Drop hospitals
    op.drop_index('idx_hospitals_geom', table_name='hospitals')
    op.drop_index(op.f('ix_hospitals_osm_id'), table_name='hospitals')
    op.drop_table('hospitals')

    # Drop buildings
    op.drop_index('idx_buildings_geom', table_name='buildings')
    op.drop_index(op.f('ix_buildings_osm_id'), table_name='buildings')
    op.drop_table('buildings')

    # Drop roads
    op.drop_index('idx_roads_geom', table_name='roads')
    op.drop_index(op.f('ix_roads_osm_id'), table_name='roads')
    op.drop_table('roads')

    # Drop wards
    op.drop_index('idx_wards_geom', table_name='wards')
    op.drop_index(op.f('ix_wards_ward_number'), table_name='wards')
    op.drop_table('wards')

    # Drop city
    op.drop_index('idx_city_geom', table_name='city')
    op.drop_table('city')

    # 20. Disable PostGIS
    op.execute("DROP EXTENSION IF EXISTS postgis")
