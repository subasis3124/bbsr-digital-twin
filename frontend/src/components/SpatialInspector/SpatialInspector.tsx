import React from 'react';
import { Eye, MapPin, X, Info, ShieldAlert, BarChart2, CheckCircle2 } from 'lucide-react';
import { ProvenanceBadge } from '../Provenance/ProvenanceBadge';

interface SelectedEntity {
  type: 'ward' | 'road' | 'resource' | 'flood_cell' | 'air_quality' | 'building';
  id: string | number;
  data: Record<string, any>;
}

interface SpatialInspectorProps {
  selectedEntity: SelectedEntity | null;
  onClose: () => void;
}

export const SpatialInspector: React.FC<SpatialInspectorProps> = ({ selectedEntity, onClose }) => {
  if (!selectedEntity) {
    return (
      <div className="glass-panel">
        <div className="panel-header">
          <span className="panel-title">
            <Eye size={16} color="var(--accent-cyan)" />
            SPATIAL INSPECTOR
          </span>
        </div>
        <div className="panel-content" style={{ textAlign: 'center', padding: '30px 14px', color: 'var(--text-muted)' }}>
          <MapPin size={28} style={{ opacity: 0.4, marginBottom: '8px' }} />
          <p style={{ fontSize: '0.82rem' }}>Select any spatial feature on the map (ward, road, grid cell, or resource) to inspect detailed telemetry.</p>
        </div>
      </div>
    );
  }

  const { type, data } = selectedEntity;

  const renderContent = () => {
    switch (type) {
      case 'ward':
        return (
          <>
            <div className="inspector-row">
              <span className="inspector-label">Ward Name</span>
              <span className="inspector-value">{data.ward_name || `Ward ${data.ward_number}`}</span>
            </div>
            <div className="inspector-row">
              <span className="inspector-label">Ward Number</span>
              <span className="inspector-value">{data.ward_number}</span>
            </div>
            <div className="inspector-row">
              <span className="inspector-label">Population</span>
              <span className="inspector-value">{data.population ? data.population.toLocaleString() : 'Data unavailable'}</span>
            </div>
            <div className="inspector-row">
              <span className="inspector-label">Area (sq km)</span>
              <span className="inspector-value">{data.area_sqkm ? data.area_sqkm.toFixed(2) : 'N/A'}</span>
            </div>
            <ProvenanceBadge status={data.data_provenance_status} isSynthetic={data.is_synthetic} warning={data.scientific_validation_warning} />
          </>
        );

      case 'road':
        return (
          <>
            <div className="inspector-row">
              <span className="inspector-label">Road Name</span>
              <span className="inspector-value">{data.name || 'Unnamed Segment'}</span>
            </div>
            <div className="inspector-row">
              <span className="inspector-label">Road ID</span>
              <span className="inspector-value">{data.road_id || data.id}</span>
            </div>
            <div className="inspector-row">
              <span className="inspector-label">Highway Type</span>
              <span className="inspector-value">{data.highway_type || 'unclassified'}</span>
            </div>
            <div className="inspector-row">
              <span className="inspector-label">Speed limit / Lanes</span>
              <span className="inspector-value">{data.maxspeed ? `${data.maxspeed} km/h` : 'N/A'} ({data.lanes || 1} lanes)</span>
            </div>
            {data.predicted_speed !== undefined && (
              <div className="inspector-row" style={{ background: 'rgba(59, 130, 246, 0.1)', padding: '6px' }}>
                <span className="inspector-label" style={{ color: 'var(--accent-blue)', fontWeight: '600' }}>
                  GNN Speed Forecast
                </span>
                <span className="inspector-value" style={{ color: 'var(--accent-blue)', fontSize: '0.95rem' }}>
                  {data.predicted_speed} km/h
                </span>
              </div>
            )}
            {data.predicted_congestion_ratio !== undefined && (
              <div className="inspector-row">
                <span className="inspector-label">Congestion Index</span>
                <span className="inspector-value">{(data.predicted_congestion_ratio * 100).toFixed(1)}%</span>
              </div>
            )}
            <ProvenanceBadge status={data.data_provenance_status} isSynthetic={data.is_synthetic} warning={data.scientific_validation_warning} sourceModel={data.gnn_architecture || 'GNN'} />
          </>
        );

      case 'resource':
        const capacityVal = (data.beds !== undefined && data.beds !== null && data.beds > 0)
          ? `${data.beds} Beds`
          : 'Capacity unavailable';

        return (
          <>
            <div className="inspector-row">
              <span className="inspector-label">Facility Name</span>
              <span className="inspector-value">{data.name || 'Emergency Facility'}</span>
            </div>
            <div className="inspector-row">
              <span className="inspector-label">Resource Type</span>
              <span className="inspector-value" style={{ textTransform: 'capitalize', color: 'var(--accent-cyan)' }}>
                {data.resource_type || 'Facility'}
              </span>
            </div>
            <div className="inspector-row">
              <span className="inspector-label">Capacity / Status</span>
              <span className="inspector-value" style={{ color: capacityVal === 'Capacity unavailable' ? 'var(--text-muted)' : 'var(--accent-emerald)' }}>
                {capacityVal}
              </span>
            </div>
            {data.osm_id && (
              <div className="inspector-row">
                <span className="inspector-label">OSM ID</span>
                <span className="inspector-value">{data.osm_id}</span>
              </div>
            )}
            {data.assigned_demand !== undefined && (
              <div className="inspector-row" style={{ background: 'rgba(20, 184, 166, 0.15)', padding: '6px' }}>
                <span className="inspector-label" style={{ color: 'var(--accent-teal)' }}>Allocated Emergency Demand</span>
                <span className="inspector-value" style={{ color: 'var(--accent-teal)' }}>{data.assigned_demand} units</span>
              </div>
            )}
          </>
        );

      case 'flood_cell':
        const prob = data.predicted_probability ? (data.predicted_probability * 100).toFixed(1) : '0';
        return (
          <>
            <div className="inspector-row">
              <span className="inspector-label">Grid Cell Code</span>
              <span className="inspector-value">{data.cell_code || `Cell ${data.cell_id}`}</span>
            </div>
            <div className="inspector-row">
              <span className="inspector-label">Flood Risk Category</span>
              <span className="inspector-value" style={{
                color: data.predicted_class === 'HIGH' || data.predicted_class === 'VERY HIGH' ? 'var(--accent-rose)' : 'var(--accent-emerald)',
                fontWeight: '700'
              }}>
                {data.predicted_class || 'LOW'}
              </span>
            </div>
            <div className="inspector-row">
              <span className="inspector-label">Flood Probability</span>
              <span className="inspector-value">{prob}%</span>
            </div>

            {data.environmental_features && (
              <div style={{ marginTop: '8px', background: 'rgba(15, 23, 42, 0.6)', padding: '8px', borderRadius: '6px' }}>
                <div style={{ fontSize: '0.75rem', fontWeight: '600', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                  ENVIRONMENTAL TELEMETRY
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '4px', fontSize: '0.72rem' }}>
                  <div>Elev: <strong>{data.environmental_features.elevation_m ?? 'N/A'}m</strong></div>
                  <div>Slope: <strong>{data.environmental_features.slope_deg ?? 'N/A'}°</strong></div>
                  <div>NDVI: <strong>{data.environmental_features.ndvi ?? 'N/A'}</strong></div>
                  <div>NDWI: <strong>{data.environmental_features.ndwi ?? 'N/A'}</strong></div>
                </div>
              </div>
            )}

            {data.feature_importance_shap && (
              <div style={{ marginTop: '8px' }}>
                <div style={{ fontSize: '0.75rem', fontWeight: '600', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                  SHAP FEATURE ATTRIBUTION
                </div>
                {Object.entries(data.feature_importance_shap).slice(0, 4).map(([feat, val]: [string, any]) => (
                  <div key={feat} className="inspector-row" style={{ fontSize: '0.72rem' }}>
                    <span className="inspector-label">{feat}</span>
                    <span className="inspector-value">{typeof val === 'number' ? val.toFixed(3) : val}</span>
                  </div>
                ))}
              </div>
            )}
            <ProvenanceBadge status={data.data_provenance_status} isSynthetic={data.is_synthetic} warning={data.scientific_validation_warning} sourceModel={data.model_name || 'XGBoost Flood Model'} />
          </>
        );

      case 'air_quality':
        return (
          <>
            <div className="inspector-row">
              <span className="inspector-label">Monitoring Station</span>
              <span className="inspector-value">{data.station_name}</span>
            </div>
            <div className="inspector-row">
              <span className="inspector-label">Pollutant</span>
              <span className="inspector-value">{data.pollutant?.toUpperCase()}</span>
            </div>
            <div className="inspector-row">
              <span className="inspector-label">Predicted Conc.</span>
              <span className="inspector-value" style={{ color: 'var(--accent-purple)', fontSize: '0.95rem' }}>
                {data.predicted_value} μg/m³
              </span>
            </div>
            <div className="inspector-row">
              <span className="inspector-label">Forecast Horizon</span>
              <span className="inspector-value">+{data.horizon_hours || 6} Hours</span>
            </div>
            <ProvenanceBadge status={data.data_provenance_status} isSynthetic={data.is_synthetic} warning={data.scientific_validation_warning} />
          </>
        );

      case 'building':
        return (
          <>
            <div className="inspector-row">
              <span className="inspector-label">Building ID</span>
              <span className="inspector-value">{data.id}</span>
            </div>
            <div className="inspector-row">
              <span className="inspector-label">Building Type</span>
              <span className="inspector-value" style={{ textTransform: 'capitalize' }}>
                {data.building_type || 'unclassified'}
              </span>
            </div>
            <div className="inspector-row">
              <span className="inspector-label">Extruded Height</span>
              <span className="inspector-value">
                {data.extrusion_height_m ? `${data.extrusion_height_m} meters` : '12 meters (Default)'}
              </span>
            </div>
            <div className="inspector-row">
              <span className="inspector-label">Height Provenance</span>
              <span className="inspector-value" style={{ color: data.is_exemplary_extrusion ? 'var(--accent-amber)' : 'var(--accent-emerald)' }}>
                {data.is_exemplary_extrusion ? 'Relative Exemplary Extrusion' : 'Observed Footprint Height'}
              </span>
            </div>
            {data.levels && (
              <div className="inspector-row">
                <span className="inspector-label">Building Levels</span>
                <span className="inspector-value">{data.levels}</span>
              </div>
            )}
            {data.osm_id && (
              <div className="inspector-row">
                <span className="inspector-label">OSM ID</span>
                <span className="inspector-value">{data.osm_id}</span>
              </div>
            )}
          </>
        );

      default:
        return null;
    }
  };

  return (
    <div className="glass-panel">
      <div className="panel-header">
        <span className="panel-title">
          <Info size={16} color="var(--accent-cyan)" />
          {type.toUpperCase()} TELEMETRY
        </span>
        <button
          onClick={onClose}
          style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
        >
          <X size={16} />
        </button>
      </div>

      <div className="panel-content spatial-inspector">
        {renderContent()}
      </div>
    </div>
  );
};
