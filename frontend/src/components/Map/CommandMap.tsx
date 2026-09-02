import React from 'react';
import { MapContainer, TileLayer, GeoJSON, CircleMarker, Polyline, Popup, Marker, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import { ActiveLayers } from '../Layers/LayerControl';
import {
  GeoJSONFeatureCollection,
  FloodRiskProperties,
  GNNTrafficProperties,
  AirQualityProperties,
  OptimizationRunDetail,
  AllocationResult
} from '../../types';

interface CommandMapProps {
  layers: ActiveLayers;
  floodData: GeoJSONFeatureCollection<FloodRiskProperties> | null;
  trafficData: GeoJSONFeatureCollection<GNNTrafficProperties> | null;
  airQualityData: GeoJSONFeatureCollection<AirQualityProperties> | null;
  hospitalsData: GeoJSONFeatureCollection | null;
  policeData: GeoJSONFeatureCollection | null;
  fireData: GeoJSONFeatureCollection | null;
  wardsData: GeoJSONFeatureCollection | null;
  roadsData: GeoJSONFeatureCollection | null;
  busStopsData: GeoJSONFeatureCollection | null;
  busRoutesData: GeoJSONFeatureCollection | null;
  waterBodiesData: GeoJSONFeatureCollection | null;
  activeOptimization: OptimizationRunDetail | null;
  onSelectEntity: (entity: { type: 'ward' | 'road' | 'resource' | 'flood_cell' | 'air_quality'; id: string | number; data: Record<string, any> }) => void;
}

// Bhubaneswar coordinates
const BHUBANESWAR_CENTER: [number, number] = [20.296, 85.824];

export const CommandMap: React.FC<CommandMapProps> = ({
  layers,
  floodData,
  trafficData,
  airQualityData,
  hospitalsData,
  policeData,
  fireData,
  wardsData,
  roadsData,
  busStopsData,
  busRoutesData,
  waterBodiesData,
  activeOptimization,
  onSelectEntity,
}) => {
  // Styling helper for flood risk grid cells
  const getFloodStyle = (feature: any) => {
    const riskClass = (feature?.properties?.predicted_class || 'LOW').toUpperCase();
    let fillColor = '#10b981'; // LOW
    if (riskClass === 'MEDIUM') fillColor = '#f59e0b';
    if (riskClass === 'HIGH') fillColor = '#f97316';
    if (riskClass === 'VERY HIGH') fillColor = '#ef4444';

    return {
      fillColor,
      weight: 1,
      opacity: 0.8,
      color: fillColor,
      fillOpacity: 0.45,
    };
  };

  // Styling helper for traffic GNN roads
  const getTrafficStyle = (feature: any) => {
    const speed = feature?.properties?.predicted_speed ?? 30;
    let color = '#10b981';
    if (speed < 20) color = '#ef4444';
    else if (speed < 40) color = '#f59e0b';

    return {
      color,
      weight: speed < 20 ? 5 : 3,
      opacity: 0.85,
    };
  };

  // Styling helper for ward boundaries
  const wardStyle = {
    fillColor: '#8b5cf6',
    weight: 2,
    opacity: 0.7,
    color: '#a855f7',
    fillOpacity: 0.1,
    dashArray: '4',
  };

  // Styling helper for generic roads
  const roadStyle = {
    color: '#475569',
    weight: 2,
    opacity: 0.6,
  };

  // Styling helper for bus routes
  const busRouteStyle = {
    color: '#ec4899',
    weight: 2,
    opacity: 0.7,
    dashArray: '3, 6',
  };

  // Styling helper for water bodies
  const waterBodyStyle = {
    fillColor: '#06b6d4',
    weight: 1,
    color: '#0284c7',
    fillOpacity: 0.5,
  };

  return (
    <div className="map-view-container">
      <MapContainer
        center={BHUBANESWAR_CENTER}
        zoom={12}
        zoomControl={false}
        className="leaflet-map"
      >
        {/* Base Map Tiles - Dark Theme */}
        <TileLayer
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />

        {/* 1. Ward Boundaries */}
        {layers.wards && wardsData && (
          <GeoJSON
            key="layer-wards"
            data={wardsData as any}
            style={wardStyle}
            onEachFeature={(feature, layer) => {
              layer.on('click', () => {
                onSelectEntity({
                  type: 'ward',
                  id: feature.properties?.id || feature.properties?.ward_number,
                  data: feature.properties,
                });
              });
            }}
          />
        )}

        {/* 2. Water Bodies */}
        {layers.waterBodies && waterBodiesData && (
          <GeoJSON
            key="layer-water-bodies"
            data={waterBodiesData as any}
            style={waterBodyStyle}
          />
        )}

        {/* 3. Base Road Network */}
        {layers.roads && roadsData && (
          <GeoJSON
            key="layer-roads"
            data={roadsData as any}
            style={roadStyle}
            onEachFeature={(feature, layer) => {
              layer.on('click', () => {
                onSelectEntity({
                  type: 'road',
                  id: feature.properties?.id,
                  data: feature.properties,
                });
              });
            }}
          />
        )}

        {/* 4. Bus Routes */}
        {layers.busRoutes && busRoutesData && (
          <GeoJSON
            key="layer-bus-routes"
            data={busRoutesData as any}
            style={busRouteStyle}
          />
        )}

        {/* 5. Flood Risk Grid Cells */}
        {layers.floodRisk && floodData && (
          <GeoJSON
            key="layer-flood-risk"
            data={floodData as any}
            style={getFloodStyle}
            onEachFeature={(feature, layer) => {
              layer.on('click', () => {
                onSelectEntity({
                  type: 'flood_cell',
                  id: feature.properties?.prediction_id || feature.properties?.cell_id,
                  data: feature.properties,
                });
              });
            }}
          />
        )}

        {/* 6. GNN Traffic Forecast Roads */}
        {layers.trafficForecast && trafficData && (
          <GeoJSON
            key="layer-traffic"
            data={trafficData as any}
            style={getTrafficStyle}
            onEachFeature={(feature, layer) => {
              layer.on('click', () => {
                onSelectEntity({
                  type: 'road',
                  id: feature.properties?.road_id,
                  data: feature.properties,
                });
              });
            }}
          />
        )}

        {/* 7. Air Quality Monitoring Stations */}
        {layers.airQuality && airQualityData && (
          <>
            {airQualityData.features.map((feat, idx) => {
              const coords = feat.geometry?.coordinates || [85.824, 20.296];
              const val = feat.properties?.predicted_value || 50;
              const lat = coords[1];
              const lng = coords[0];
              return (
                <CircleMarker
                  key={`aq-${idx}`}
                  center={[lat, lng]}
                  radius={10}
                  pathOptions={{
                    fillColor: val > 100 ? '#ef4444' : val > 50 ? '#f59e0b' : '#8b5cf6',
                    fillOpacity: 0.8,
                    color: '#ffffff',
                    weight: 2,
                  }}
                  eventHandlers={{
                    click: () => {
                      onSelectEntity({
                        type: 'air_quality',
                        id: feat.properties.prediction_id || idx,
                        data: feat.properties,
                      });
                    },
                  }}
                >
                  <Popup>
                    <strong>{feat.properties.station_name}</strong>
                    <br />
                    AQI Value: {val} μg/m³
                  </Popup>
                </CircleMarker>
              );
            })}
          </>
        )}

        {/* 8. Hospitals */}
        {layers.hospitals && hospitalsData && (
          <>
            {hospitalsData.features.map((feat, idx) => {
              const coords = feat.geometry?.coordinates;
              if (!coords) return null;
              return (
                <CircleMarker
                  key={`hosp-${idx}`}
                  center={[coords[1], coords[0]]}
                  radius={7}
                  pathOptions={{
                    fillColor: '#38bdf8',
                    fillOpacity: 0.9,
                    color: '#0284c7',
                    weight: 2,
                  }}
                  eventHandlers={{
                    click: () => {
                      onSelectEntity({
                        type: 'resource',
                        id: feat.properties?.id || idx,
                        data: { ...feat.properties, resource_type: 'hospital' },
                      });
                    },
                  }}
                >
                  <Popup>
                    <strong>{feat.properties?.name || 'Hospital'}</strong>
                    <br />
                    {feat.properties?.beds ? `${feat.properties.beds} Beds` : 'Capacity unavailable'}
                  </Popup>
                </CircleMarker>
              );
            })}
          </>
        )}

        {/* 9. Police Stations */}
        {layers.policeStations && policeData && (
          <>
            {policeData.features.map((feat, idx) => {
              const coords = feat.geometry?.coordinates;
              if (!coords) return null;
              return (
                <CircleMarker
                  key={`police-${idx}`}
                  center={[coords[1], coords[0]]}
                  radius={6}
                  pathOptions={{
                    fillColor: '#6366f1',
                    fillOpacity: 0.9,
                    color: '#4338ca',
                    weight: 2,
                  }}
                  eventHandlers={{
                    click: () => {
                      onSelectEntity({
                        type: 'resource',
                        id: feat.properties?.id || idx,
                        data: { ...feat.properties, resource_type: 'police_station' },
                      });
                    },
                  }}
                >
                  <Popup>
                    <strong>{feat.properties?.name || 'Police Station'}</strong>
                  </Popup>
                </CircleMarker>
              );
            })}
          </>
        )}

        {/* 10. Fire Stations */}
        {layers.fireStations && fireData && (
          <>
            {fireData.features.map((feat, idx) => {
              const coords = feat.geometry?.coordinates;
              if (!coords) return null;
              return (
                <CircleMarker
                  key={`fire-${idx}`}
                  center={[coords[1], coords[0]]}
                  radius={6}
                  pathOptions={{
                    fillColor: '#f97316',
                    fillOpacity: 0.9,
                    color: '#c2410c',
                    weight: 2,
                  }}
                  eventHandlers={{
                    click: () => {
                      onSelectEntity({
                        type: 'resource',
                        id: feat.properties?.id || idx,
                        data: { ...feat.properties, resource_type: 'fire_station' },
                      });
                    },
                  }}
                >
                  <Popup>
                    <strong>{feat.properties?.name || 'Fire Station'}</strong>
                  </Popup>
                </CircleMarker>
              );
            })}
          </>
        )}

        {/* 11. Bus Stops */}
        {layers.busStops && busStopsData && (
          <>
            {busStopsData.features.map((feat, idx) => {
              const coords = feat.geometry?.coordinates;
              if (!coords) return null;
              return (
                <CircleMarker
                  key={`bus-stop-${idx}`}
                  center={[coords[1], coords[0]]}
                  radius={3}
                  pathOptions={{
                    fillColor: '#eab308',
                    fillOpacity: 0.8,
                    color: '#ca8a04',
                    weight: 1,
                  }}
                />
              );
            })}
          </>
        )}

        {/* 12. Emergency Optimization Vectors */}
        {layers.allocations && activeOptimization?.allocations && (
          <>
            {activeOptimization.allocations.map((alloc: AllocationResult, idx: number) => {
              const demandLat = alloc.demand_location[1];
              const demandLng = alloc.demand_location[0];
              const resLat = alloc.resource_location[1];
              const resLng = alloc.resource_location[0];

              return (
                <React.Fragment key={`alloc-vec-${idx}`}>
                  {/* Directional connecting polyline */}
                  <Polyline
                    positions={[
                      [demandLat, demandLng],
                      [resLat, resLng],
                    ]}
                    pathOptions={{
                      color: '#14b8a6',
                      weight: 3,
                      dashArray: '6, 6',
                      opacity: 0.9,
                    }}
                  />
                  {/* Demand point marker */}
                  <CircleMarker
                    center={[demandLat, demandLng]}
                    radius={5}
                    pathOptions={{
                      fillColor: '#f43f5e',
                      fillOpacity: 1,
                      color: '#ffffff',
                      weight: 1.5,
                    }}
                  >
                    <Popup>
                      <strong>Demand Incident ({alloc.demand_id})</strong>
                      <br />
                      Assigned Resource: {alloc.resource_id}
                      <br />
                      Travel Time: {alloc.travel_time_minutes.toFixed(1)} mins
                    </Popup>
                  </CircleMarker>
                </React.Fragment>
              );
            })}
          </>
        )}
      </MapContainer>
    </div>
  );
};
