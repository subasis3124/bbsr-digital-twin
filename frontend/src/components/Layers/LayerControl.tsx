import React from 'react';
import { Layers, Eye, EyeOff, AlertTriangle, Car, Wind, Hospital, Shield, Flame, MapPin, Bus, Waves, Route, Layers3, Building2, Mountain } from 'lucide-react';

export interface ActiveLayers {
  terrain: boolean;
  buildings: boolean;
  floodRisk: boolean;
  trafficForecast: boolean;
  airQuality: boolean;
  hospitals: boolean;
  policeStations: boolean;
  fireStations: boolean;
  wards: boolean;
  roads: boolean;
  busStops: boolean;
  busRoutes: boolean;
  waterBodies: boolean;
  allocations: boolean;
}

interface LayerControlProps {
  layers: ActiveLayers;
  onToggleLayer: (layerName: keyof ActiveLayers) => void;
}

export const LayerControl: React.FC<LayerControlProps> = ({ layers, onToggleLayer }) => {
  const layerItems: { key: keyof ActiveLayers; label: string; icon: any; color: string }[] = [
    { key: 'terrain', label: '3D Terrain Elevation', icon: Mountain, color: '#38bdf8' },
    { key: 'buildings', label: '3D Building Footprints', icon: Building2, color: '#f472b6' },
    { key: 'floodRisk', label: 'Flood Risk (Grid)', icon: AlertTriangle, color: 'var(--accent-rose)' },
    { key: 'trafficForecast', label: 'Traffic Forecast (GNN)', icon: Car, color: 'var(--accent-blue)' },
    { key: 'airQuality', label: 'Air Quality (Stations)', icon: Wind, color: 'var(--accent-purple)' },
    { key: 'allocations', label: 'Emergency Allocations', icon: Route, color: 'var(--accent-teal)' },
    { key: 'hospitals', label: 'Hospitals', icon: Hospital, color: '#38bdf8' },
    { key: 'policeStations', label: 'Police Stations', icon: Shield, color: '#6366f1' },
    { key: 'fireStations', label: 'Fire Stations', icon: Flame, color: '#f97316' },
    { key: 'wards', label: 'Ward Boundaries', icon: Layers3, color: '#a855f7' },
    { key: 'roads', label: 'Road Network', icon: MapPin, color: '#94a3b8' },
    { key: 'busStops', label: 'Bus Stops', icon: Bus, color: '#eab308' },
    { key: 'busRoutes', label: 'Bus Routes', icon: Route, color: '#ec4899' },
    { key: 'waterBodies', label: 'Water Bodies', icon: Waves, color: '#06b6d4' },
  ];

  return (
    <div className="glass-panel">
      <div className="panel-header">
        <span className="panel-title">
          <Layers size={16} color="var(--accent-cyan)" />
          SPATIAL LAYERS & LEGEND
        </span>
      </div>

      <div className="panel-content" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {layerItems.map((item) => {
            const Icon = item.icon;
            const isActive = layers[item.key];
            return (
              <div
                key={item.key}
                onClick={() => onToggleLayer(item.key)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '6px 10px',
                  borderRadius: '6px',
                  background: isActive ? 'rgba(30, 41, 59, 0.7)' : 'transparent',
                  border: isActive ? '1px solid rgba(56, 189, 248, 0.3)' : '1px solid transparent',
                  cursor: 'pointer',
                  fontSize: '0.8rem',
                  transition: 'all 0.15s ease'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Icon size={14} color={isActive ? item.color : 'var(--text-muted)'} />
                  <span style={{ color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
                    {item.label}
                  </span>
                </div>
                {isActive ? (
                  <Eye size={13} color="var(--accent-cyan)" />
                ) : (
                  <EyeOff size={13} color="var(--text-muted)" />
                )}
              </div>
            );
          })}
        </div>

        {/* Dynamic Legends */}
        <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px solid var(--border-card)' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: '600', color: 'var(--text-secondary)', marginBottom: '6px' }}>
            ACTIVE LEGENDS
          </div>

          {layers.buildings && (
            <div className="legend-box" style={{ marginBottom: '8px' }}>
              <div style={{ fontWeight: '600', color: 'var(--text-muted)' }}>3D Building Footprints</div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                Extruded by height attribute / 12m exemplary default where observed height missing.
              </div>
            </div>
          )}

          {layers.floodRisk && (
            <div className="legend-box" style={{ marginBottom: '8px' }}>
              <div style={{ fontWeight: '600', color: 'var(--text-muted)' }}>Flood Risk Categories</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '4px' }}>
                <div className="legend-item"><div className="legend-color-dot" style={{ background: '#10b981' }} /> Low</div>
                <div className="legend-item"><div className="legend-color-dot" style={{ background: '#f59e0b' }} /> Medium</div>
                <div className="legend-item"><div className="legend-color-dot" style={{ background: '#f97316' }} /> High</div>
                <div className="legend-item"><div className="legend-color-dot" style={{ background: '#ef4444' }} /> Very High</div>
              </div>
            </div>
          )}

          {layers.trafficForecast && (
            <div className="legend-box" style={{ marginBottom: '8px' }}>
              <div style={{ fontWeight: '600', color: 'var(--text-muted)' }}>GNN Traffic Speed (km/h)</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '4px' }}>
                <div className="legend-item"><div className="legend-color-dot" style={{ background: '#10b981' }} /> &gt; 40 km/h (Free)</div>
                <div className="legend-item"><div className="legend-color-dot" style={{ background: '#f59e0b' }} /> 20 - 40 (Moderate)</div>
                <div className="legend-item"><div className="legend-color-dot" style={{ background: '#ef4444' }} /> &lt; 20 (Heavy)</div>
              </div>
            </div>
          )}

          {layers.allocations && (
            <div className="legend-box">
              <div style={{ fontWeight: '600', color: 'var(--text-muted)' }}>Optimization Allocations</div>
              <div className="legend-item">
                <div className="legend-color-dot" style={{ background: '#14b8a6', height: '3px', width: '16px' }} />
                <span>Demand Point → Resource</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
