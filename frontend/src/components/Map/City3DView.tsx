import React, { useEffect, useRef, useState } from 'react';
import * as Cesium from 'cesium';
import 'cesium/Build/Cesium/Widgets/widgets.css';
import { AlertTriangle, Compass, RotateCcw, ShieldAlert, Mountain, Layers, Eye } from 'lucide-react';
import { ActiveLayers } from '../Layers/LayerControl';
import {
  GeoJSONFeatureCollection,
  FloodRiskProperties,
  GNNTrafficProperties,
  AirQualityProperties,
  BuildingProperties,
  SimulationRunDetail,
  OptimizationRunDetail,
} from '../../types';
import { ProvenanceBadge } from '../Provenance/ProvenanceBadge';

interface City3DViewProps {
  layers: ActiveLayers;
  floodData: GeoJSONFeatureCollection<FloodRiskProperties> | null;
  trafficData: GeoJSONFeatureCollection<GNNTrafficProperties> | null;
  airQualityData: GeoJSONFeatureCollection<AirQualityProperties> | null;
  hospitalsData: GeoJSONFeatureCollection | null;
  policeData: GeoJSONFeatureCollection | null;
  fireData: GeoJSONFeatureCollection | null;
  wardsData: GeoJSONFeatureCollection | null;
  roadsData: GeoJSONFeatureCollection | null;
  buildingsData: GeoJSONFeatureCollection<BuildingProperties> | null;
  busStopsData: GeoJSONFeatureCollection | null;
  busRoutesData: GeoJSONFeatureCollection | null;
  waterBodiesData: GeoJSONFeatureCollection | null;
  activeSimulation: SimulationRunDetail | null;
  activeOptimization: OptimizationRunDetail | null;
  onSelectEntity: (entity: {
    type: 'ward' | 'road' | 'resource' | 'flood_cell' | 'air_quality' | 'building';
    id: string | number;
    data: Record<string, any>;
  } | null) => void;
  onSwitchTo2D?: () => void;
}

const BHUBANESWAR_CENTER = {
  longitude: 85.8245,
  latitude: 20.2961,
  height: 6000,
  heading: 0,
  pitch: -45,
  roll: 0,
};

function isWebGLSupported(): boolean {
  try {
    const canvas = document.createElement('canvas');
    return !!(
      window.WebGLRenderingContext &&
      (canvas.getContext('webgl') || canvas.getContext('experimental-webgl'))
    );
  } catch (e) {
    return false;
  }
}

export const City3DView: React.FC<City3DViewProps> = ({
  layers,
  floodData,
  trafficData,
  airQualityData,
  hospitalsData,
  policeData,
  fireData,
  wardsData,
  roadsData,
  buildingsData,
  busStopsData,
  busRoutesData,
  waterBodiesData,
  activeSimulation,
  activeOptimization,
  onSelectEntity,
  onSwitchTo2D,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<Cesium.Viewer | null>(null);
  const [webGlAvailable, setWebGlAvailable] = useState<boolean>(true);
  const [terrainStatus, setTerrainStatus] = useState<string>('Ellipsoid Terrain');
  const [renderError, setRenderError] = useState<string | null>(null);

  // Initialize Cesium Viewer
  useEffect(() => {
    if (!isWebGLSupported()) {
      setWebGlAvailable(false);
      return;
    }

    if (!containerRef.current) return;

    let viewer: Cesium.Viewer | null = null;
    try {
      // Configure Ion Token from env variable if available
      const ionToken = import.meta.env.VITE_CESIUM_ION_TOKEN;
      if (ionToken) {
        Cesium.Ion.defaultAccessToken = ionToken;
        setTerrainStatus('Cesium Ion World Terrain');
      } else {
        setTerrainStatus('Terrain unavailable (Default Ellipsoid)');
      }

      viewer = new Cesium.Viewer(containerRef.current, {
        animation: false,
        timeline: false,
        geocoder: false,
        homeButton: false,
        sceneModePicker: false,
        baseLayerPicker: false,
        navigationHelpButton: false,
        fullscreenButton: false,
        selectionIndicator: true,
        infoBox: false, // We use SpatialInspector for custom entity UI
        terrainProvider: new Cesium.EllipsoidTerrainProvider(),
      });

      // Disable default double-click entity zoom
      viewer.screenSpaceEventHandler.removeInputAction(
        Cesium.ScreenSpaceEventType.LEFT_DOUBLE_CLICK
      );

      // Initial Camera fly to Bhubaneswar
      viewer.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(
          BHUBANESWAR_CENTER.longitude,
          BHUBANESWAR_CENTER.latitude,
          BHUBANESWAR_CENTER.height
        ),
        orientation: {
          heading: Cesium.Math.toRadians(BHUBANESWAR_CENTER.heading),
          pitch: Cesium.Math.toRadians(BHUBANESWAR_CENTER.pitch),
          roll: Cesium.Math.toRadians(BHUBANESWAR_CENTER.roll),
        },
        duration: 1.5,
      });

      // Entity Click Handling (ScreenSpaceEventHandler)
      const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
      handler.setInputAction((click: { position: Cesium.Cartesian2 }) => {
        if (!viewer) return;
        const pickedObject = viewer.scene.pick(click.position);
        if (Cesium.defined(pickedObject) && pickedObject.id) {
          const entity = pickedObject.id as Cesium.Entity;
          const customProps = entity.properties?.getValue(Cesium.JulianDate.now());
          if (customProps && customProps.entityType) {
            onSelectEntity({
              type: customProps.entityType,
              id: customProps.id || entity.id,
              data: customProps,
            });
          }
        }
      }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

      viewerRef.current = viewer;
    } catch (err: any) {
      console.error('Failed to initialize 3D WebGL Viewer:', err);
      setRenderError(err?.message || 'WebGL context creation error');
      setWebGlAvailable(false);
    }

    return () => {
      if (viewerRef.current && !viewerRef.current.isDestroyed()) {
        try {
          viewerRef.current.destroy();
        } catch (e) {
          console.warn('Error destroying Cesium viewer:', e);
        }
        viewerRef.current = null;
      }
    };
  }, []);

  // Update Entities & Layers in Cesium Viewer whenever state/data changes
  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || viewer.isDestroyed()) return;

    viewer.entities.removeAll();

    // 1. Wards Layer
    if (layers.wards && wardsData?.features) {
      wardsData.features.forEach((feature) => {
        if (feature.geometry.type === 'Polygon' || feature.geometry.type === 'MultiPolygon') {
          const coords = feature.geometry.coordinates;
          const rings = feature.geometry.type === 'Polygon' ? [coords[0]] : coords.map((c: any) => c[0]);
          rings.forEach((ring: any) => {
            const flatDegrees: number[] = [];
            ring.forEach(([lon, lat]: [number, number]) => {
              flatDegrees.push(lon, lat);
            });

            viewer.entities.add({
              name: `Ward ${feature.properties.ward_number || feature.properties.ward_name}`,
              properties: new Cesium.PropertyBag({
                entityType: 'ward',
                id: feature.properties.id,
                ...feature.properties,
              }),
              polygon: {
                hierarchy: Cesium.Cartesian3.fromDegreesArray(flatDegrees),
                material: Cesium.Color.fromCssColorString('#a855f7').withAlpha(0.15),
                outline: true,
                outlineColor: Cesium.Color.fromCssColorString('#a855f7'),
                outlineWidth: 2,
              },
            });
          });
        }
      });
    }

    // 2. Buildings 3D Layer
    if (layers.buildings && buildingsData?.features) {
      buildingsData.features.forEach((feature) => {
        if (feature.geometry.type === 'Polygon') {
          const ring = feature.geometry.coordinates[0];
          const flatDegrees: number[] = [];
          ring.forEach(([lon, lat]: [number, number]) => {
            flatDegrees.push(lon, lat);
          });

          // Height extrusion logic: height attribute or levels * 3.5m or relative 12m default
          const observedHeight = feature.properties.height;
          const levels = feature.properties.levels;
          const extrusion = observedHeight || (levels ? levels * 3.5 : 12);
          const isExemplaryDefault = !observedHeight && !levels;

          viewer.entities.add({
            name: `Building ${feature.properties.id}`,
            properties: new Cesium.PropertyBag({
              ...feature.properties,
              entityType: 'building',
              id: feature.properties.id,
              extrusion_height_m: extrusion,
              is_exemplary_extrusion: isExemplaryDefault,
            }),
            polygon: {
              hierarchy: Cesium.Cartesian3.fromDegreesArray(flatDegrees),
              extrudedHeight: extrusion,
              material: Cesium.Color.fromCssColorString('#64748b').withAlpha(0.85),
              outline: true,
              outlineColor: Cesium.Color.fromCssColorString('#94a3b8'),
            },
          });
        }
      });
    }

    // 3. Flood Risk 3D Layer
    if (layers.floodRisk && floodData?.features) {
      floodData.features.forEach((feature) => {
        const prob = feature.properties.predicted_probability || 0;
        const cat = feature.properties.predicted_class || 'LOW';
        let colorHex = '#10b981';
        if (cat === 'MEDIUM') colorHex = '#f59e0b';
        if (cat === 'HIGH') colorHex = '#f97316';
        if (cat === 'VERY HIGH') colorHex = '#ef4444';

        // Simulation impact override
        const isSimulatedImpact =
          activeSimulation &&
          activeSimulation.scenario_type === 'heavy_rainfall' &&
          prob > 0.5;

        if (isSimulatedImpact) {
          colorHex = '#dc2626';
        }

        const extrudedHeight = prob * 80 + 10; // Probability extrusion height

        if (feature.geometry.type === 'Polygon') {
          const ring = feature.geometry.coordinates[0];
          const flatDegrees: number[] = [];
          ring.forEach(([lon, lat]: [number, number]) => {
            flatDegrees.push(lon, lat);
          });

          viewer.entities.add({
            name: `Flood Risk Cell ${feature.properties.cell_code}`,
            properties: new Cesium.PropertyBag({
              ...feature.properties,
              entityType: 'flood_cell',
              id: feature.properties.prediction_id || feature.properties.cell_id,
              probability_pct: Math.round(prob * 100),
              model_type: 'Flood Risk Model',
            }),
            polygon: {
              hierarchy: Cesium.Cartesian3.fromDegreesArray(flatDegrees),
              extrudedHeight: extrudedHeight,
              material: Cesium.Color.fromCssColorString(colorHex).withAlpha(0.7),
              outline: true,
              outlineColor: Cesium.Color.fromCssColorString(colorHex),
            },
          });
        }
      });
    }

    // 4. Roads & Traffic GNN Layer
    if ((layers.roads || layers.trafficForecast) && roadsData?.features) {
      // Map traffic forecast by road_id if trafficForecast is active
      const trafficMap = new Map<number, GNNTrafficProperties>();
      if (layers.trafficForecast && trafficData?.features) {
        trafficData.features.forEach((tf) => {
          if (tf.properties.road_id) {
            trafficMap.set(tf.properties.road_id, tf.properties);
          }
        });
      }

      roadsData.features.forEach((feature) => {
        if (feature.geometry.type === 'LineString') {
          const flatDegrees: number[] = [];
          feature.geometry.coordinates.forEach(([lon, lat]: [number, number]) => {
            flatDegrees.push(lon, lat);
          });

          let strokeColor = '#94a3b8';
          let strokeWidth = 3;
          const tfProps = trafficMap.get(feature.properties.id);

          if (layers.trafficForecast && tfProps) {
            const speed = tfProps.predicted_speed;
            if (speed >= 40) strokeColor = '#10b981';
            else if (speed >= 20) strokeColor = '#f59e0b';
            else strokeColor = '#ef4444';
            strokeWidth = 4;
          }

          // Simulation road closure override
          if (
            activeSimulation &&
            activeSimulation.scenario_type === 'road_closure' &&
            activeSimulation.parameters?.closed_road_ids?.includes(feature.properties.id)
          ) {
            strokeColor = '#dc2626';
            strokeWidth = 6;
          }

          viewer.entities.add({
            name: `Road ${feature.properties.name || feature.properties.id}`,
            properties: new Cesium.PropertyBag({
              entityType: 'road',
              id: feature.properties.id,
              speed_forecast_kmh: tfProps?.predicted_speed,
              traffic_provenance: tfProps?.data_provenance_status || 'FORECAST',
              ...feature.properties,
            }),
            polyline: {
              positions: Cesium.Cartesian3.fromDegreesArray(flatDegrees),
              width: strokeWidth,
              material: Cesium.Color.fromCssColorString(strokeColor),
            },
          });
        }
      });
    }

    // 5. Air Quality Stations 3D Markers
    if (layers.airQuality && airQualityData?.features) {
      airQualityData.features.forEach((feature) => {
        if (feature.geometry.type === 'Point') {
          const [lon, lat] = feature.geometry.coordinates;
          const val = feature.properties.predicted_value || 0;

          viewer.entities.add({
            name: `AQI Station ${feature.properties.station_name}`,
            properties: new Cesium.PropertyBag({
              entityType: 'air_quality',
              id: feature.properties.prediction_id,
              ...feature.properties,
            }),
            position: Cesium.Cartesian3.fromDegrees(lon, lat, val * 3),
            cylinder: {
              length: val * 6 + 50,
              topRadius: 25,
              bottomRadius: 25,
              material: Cesium.Color.fromCssColorString('#a855f7').withAlpha(0.8),
            },
          });
        }
      });
    }

    // 6. Emergency Facilities (Hospitals, Police, Fire)
    const addResourceEntities = (
      geoData: GeoJSONFeatureCollection | null,
      colorHex: string,
      resType: string
    ) => {
      if (!geoData?.features) return;
      geoData.features.forEach((feature) => {
        if (feature.geometry.type === 'Point') {
          const [lon, lat] = feature.geometry.coordinates;
          viewer.entities.add({
            name: feature.properties.name || resType,
            properties: new Cesium.PropertyBag({
              entityType: 'resource',
              id: feature.properties.id,
              resource_type: resType,
              ...feature.properties,
            }),
            position: Cesium.Cartesian3.fromDegrees(lon, lat, 60),
            cylinder: {
              length: 120,
              topRadius: 35,
              bottomRadius: 35,
              material: Cesium.Color.fromCssColorString(colorHex),
            },
          });
        }
      });
    };

    if (layers.hospitals) addResourceEntities(hospitalsData, '#ef4444', 'Hospital');
    if (layers.policeStations) addResourceEntities(policeData, '#3b82f6', 'Police Station');
    if (layers.fireStations) addResourceEntities(fireData, '#f97316', 'Fire Station');

    // 7. Bus Routes & Bus Stops
    if (layers.busRoutes && busRoutesData?.features) {
      busRoutesData.features.forEach((feature) => {
        if (feature.geometry.type === 'LineString') {
          const flatDegrees: number[] = [];
          feature.geometry.coordinates.forEach(([lon, lat]: [number, number]) => {
            flatDegrees.push(lon, lat);
          });
          viewer.entities.add({
            name: `Bus Route ${feature.properties.route_name || feature.properties.id}`,
            polyline: {
              positions: Cesium.Cartesian3.fromDegreesArray(flatDegrees),
              width: 3,
              material: Cesium.Color.fromCssColorString('#ec4899'),
            },
          });
        }
      });
    }

    if (layers.busStops && busStopsData?.features) {
      busStopsData.features.forEach((feature) => {
        if (feature.geometry.type === 'Point') {
          const [lon, lat] = feature.geometry.coordinates;
          viewer.entities.add({
            name: `Bus Stop ${feature.properties.stop_name || feature.properties.id}`,
            position: Cesium.Cartesian3.fromDegrees(lon, lat, 10),
            point: {
              pixelSize: 8,
              color: Cesium.Color.fromCssColorString('#eab308'),
              outlineColor: Cesium.Color.BLACK,
              outlineWidth: 1,
            },
          });
        }
      });
    }

    // 8. Water Bodies
    if (layers.waterBodies && waterBodiesData?.features) {
      waterBodiesData.features.forEach((feature) => {
        if (feature.geometry.type === 'Polygon') {
          const ring = feature.geometry.coordinates[0];
          const flatDegrees: number[] = [];
          ring.forEach(([lon, lat]: [number, number]) => {
            flatDegrees.push(lon, lat);
          });

          viewer.entities.add({
            name: `Water Body ${feature.properties.name || feature.properties.id}`,
            polygon: {
              hierarchy: Cesium.Cartesian3.fromDegreesArray(flatDegrees),
              material: Cesium.Color.fromCssColorString('#06b6d4').withAlpha(0.6),
            },
          });
        }
      });
    }

    // 9. Optimization Allocation Vectors (3D Arcs)
    if (layers.allocations && activeOptimization?.allocations) {
      activeOptimization.allocations.forEach((alloc, idx) => {
        const [dLon, dLat] = alloc.demand_location;
        const [rLon, rLat] = alloc.resource_location;

        let strokeColor = '#14b8a6';
        if (alloc.resource_type === 'hospital') strokeColor = '#f43f5e';
        if (alloc.resource_type === 'police_station') strokeColor = '#3b82f6';
        if (alloc.resource_type === 'fire_station') strokeColor = '#f97316';

        // Draw 3D curved polyline arc connecting demand to assigned resource
        const midLon = (dLon + rLon) / 2;
        const midLat = (dLat + rLat) / 2;
        const arcHeight = 350 + idx * 20;

        const positions = [
          Cesium.Cartesian3.fromDegrees(dLon, dLat, 10),
          Cesium.Cartesian3.fromDegrees(midLon, midLat, arcHeight),
          Cesium.Cartesian3.fromDegrees(rLon, rLat, 60),
        ];

        viewer.entities.add({
          name: `Allocation ${alloc.demand_id} → ${alloc.resource_id}`,
          properties: new Cesium.PropertyBag({
            entityType: 'allocation',
            id: `${alloc.demand_id}-${alloc.resource_id}`,
            assigned_capacity: alloc.assigned_capacity,
            travel_time_minutes: alloc.travel_time_minutes,
            provenance_status: 'DECISION SUPPORT (RECOMMENDATION)',
          }),
          polyline: {
            positions: positions,
            width: 4,
            material: Cesium.Color.fromCssColorString(strokeColor),
          },
        });
      });
    }
  }, [
    layers,
    floodData,
    trafficData,
    airQualityData,
    hospitalsData,
    policeData,
    fireData,
    wardsData,
    roadsData,
    buildingsData,
    busStopsData,
    busRoutesData,
    waterBodiesData,
    activeSimulation,
    activeOptimization,
  ]);

  // Reset Camera View Handler
  const handleResetCamera = () => {
    const viewer = viewerRef.current;
    if (!viewer || viewer.isDestroyed()) return;
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(
        BHUBANESWAR_CENTER.longitude,
        BHUBANESWAR_CENTER.latitude,
        BHUBANESWAR_CENTER.height
      ),
      orientation: {
        heading: Cesium.Math.toRadians(BHUBANESWAR_CENTER.heading),
        pitch: Cesium.Math.toRadians(BHUBANESWAR_CENTER.pitch),
        roll: Cesium.Math.toRadians(BHUBANESWAR_CENTER.roll),
      },
      duration: 1.2,
    });
  };

  // Fallback for devices without WebGL
  if (!webGlAvailable) {
    return (
      <div
        className="glass-panel"
        style={{
          height: '100%',
          width: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '24px',
          textAlign: 'center',
          gap: '16px',
          background: 'rgba(15, 23, 42, 0.95)',
        }}
      >
        <AlertTriangle size={48} color="var(--accent-rose)" />
        <div style={{ fontSize: '1.2rem', fontWeight: '700', color: 'var(--text-primary)' }}>
          3D GIS Visualization Unavailable
        </div>
        <p style={{ color: 'var(--text-secondary)', maxWidth: '420px', fontSize: '0.88rem' }}>
          {renderError || 'WebGL context is unavailable or disabled on this browser/device.'}
        </p>
        <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
          Please use the 2D Command Center mode to access all spatial intelligence features.
        </div>
        {onSwitchTo2D && (
          <button className="primary-btn" onClick={onSwitchTo2D} style={{ marginTop: '12px' }}>
            Return to 2D Command Center
          </button>
        )}
      </div>
    );
  }

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', overflow: 'hidden' }}>
      {/* Cesium Canvas Container */}
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />

      {/* Floating 3D Toolbar & Controls */}
      <div
        style={{
          position: 'absolute',
          top: '16px',
          right: '16px',
          zIndex: 10,
          display: 'flex',
          gap: '8px',
          alignItems: 'center',
        }}
      >
        <button
          className="action-btn"
          onClick={handleResetCamera}
          title="Reset Camera Target to Bhubaneswar"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            background: 'rgba(15, 23, 42, 0.85)',
            backdropFilter: 'blur(8px)',
            border: '1px solid var(--border-card)',
            color: 'var(--text-primary)',
            padding: '6px 12px',
            borderRadius: '6px',
            fontSize: '0.78rem',
            cursor: 'pointer',
          }}
        >
          <RotateCcw size={14} color="var(--accent-cyan)" /> Reset Camera
        </button>
      </div>

      {/* Terrain & System Provenance Badges Overlay */}
      <div
        style={{
          position: 'absolute',
          bottom: '24px',
          left: '16px',
          zIndex: 10,
          display: 'flex',
          flexDirection: 'column',
          gap: '6px',
          pointerEvents: 'none',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '4px 10px',
            borderRadius: '4px',
            background: 'rgba(15, 23, 42, 0.85)',
            border: '1px solid var(--border-card)',
            fontSize: '0.72rem',
            color: 'var(--text-secondary)',
            backdropFilter: 'blur(6px)',
          }}
        >
          <Mountain size={12} color="var(--accent-cyan)" />
          <span>{terrainStatus}</span>
        </div>

        {activeSimulation && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 10px',
              borderRadius: '4px',
              background: 'rgba(239, 68, 68, 0.2)',
              border: '1px solid #ef4444',
              fontSize: '0.75rem',
              color: '#fca5a5',
              backdropFilter: 'blur(6px)',
              fontWeight: '600',
            }}
          >
            <ShieldAlert size={14} color="#ef4444" />
            <span>COUNTERFACTUAL SIMULATION: {activeSimulation.scenario_name}</span>
          </div>
        )}

        {activeOptimization && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 10px',
              borderRadius: '4px',
              background: 'rgba(20, 184, 166, 0.2)',
              border: '1px solid #14b8a6',
              fontSize: '0.75rem',
              color: '#5eead4',
              backdropFilter: 'blur(6px)',
              fontWeight: '600',
            }}
          >
            <Layers size={14} color="#14b8a6" />
            <span>DECISION SUPPORT: Emergency Optimization Vectors Active</span>
          </div>
        )}
      </div>
    </div>
  );
};
