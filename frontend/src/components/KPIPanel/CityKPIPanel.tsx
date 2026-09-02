import React from 'react';
import { Activity, AlertTriangle, Car, Wind, Hospital, Shield, Flame, MapPin, Building2 } from 'lucide-react';
import { DashboardSummary } from '../../types';

interface CityKPIPanelProps {
  summary: DashboardSummary | null;
  loading: boolean;
}

export const CityKPIPanel: React.FC<CityKPIPanelProps> = ({ summary, loading }) => {
  if (loading && !summary) {
    return (
      <div className="glass-panel" style={{ padding: '16px' }}>
        <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Loading City State KPIs...</div>
      </div>
    );
  }

  const floodHighRisk = summary?.flood_risk.high_risk_cells_count ?? 0;
  const avgSpeed = summary?.traffic.average_speed_kmh ?? 0;
  const avgAQI = summary?.air_quality.average_pollutant_value ?? 0;
  const hospitalCount = summary?.infrastructure.hospitals ?? 0;
  const policeCount = summary?.infrastructure.police_stations ?? 0;
  const fireCount = summary?.infrastructure.fire_stations ?? 0;

  return (
    <div className="glass-panel">
      <div className="panel-header">
        <span className="panel-title">
          <Activity size={16} color="var(--accent-cyan)" />
          CITY STATE OVERVIEW
        </span>
        <span style={{ fontSize: '0.72rem', color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)' }}>
          EPSG:4326
        </span>
      </div>

      <div className="panel-content">
        <div className="kpi-grid">
          <div className="kpi-card" style={{ borderColor: floodHighRisk > 0 ? 'rgba(239, 68, 68, 0.4)' : undefined }}>
            <div className="kpi-card-header">
              <span>FLOOD RISK</span>
              <AlertTriangle size={14} color={floodHighRisk > 0 ? 'var(--accent-rose)' : 'var(--accent-emerald)'} />
            </div>
            <div className="kpi-val" style={{ color: floodHighRisk > 0 ? 'var(--accent-rose)' : 'var(--accent-emerald)' }}>
              {floodHighRisk}
            </div>
            <div className="kpi-sub">High/Critical Cells</div>
          </div>

          <div className="kpi-card">
            <div className="kpi-card-header">
              <span>TRAFFIC SPEED</span>
              <Car size={14} color="var(--accent-blue)" />
            </div>
            <div className="kpi-val">{avgSpeed} <span style={{ fontSize: '0.8rem', fontWeight: '400' }}>km/h</span></div>
            <div className="kpi-sub">{summary?.traffic.congested_segments_count ?? 0} Congested</div>
          </div>

          <div className="kpi-card">
            <div className="kpi-card-header">
              <span>AIR QUALITY</span>
              <Wind size={14} color="var(--accent-purple)" />
            </div>
            <div className="kpi-val">{avgAQI} <span style={{ fontSize: '0.8rem', fontWeight: '400' }}>μg/m³</span></div>
            <div className="kpi-sub">PM2.5 Average</div>
          </div>

          <div className="kpi-card">
            <div className="kpi-card-header">
              <span>RESOURCES</span>
              <Hospital size={14} color="var(--accent-teal)" />
            </div>
            <div className="kpi-val">{hospitalCount + policeCount + fireCount}</div>
            <div className="kpi-sub">Hosp: {hospitalCount} | Pol: {policeCount} | Fire: {fireCount}</div>
          </div>
        </div>

        <div style={{ marginTop: '14px', paddingTop: '12px', borderTop: '1px solid var(--border-card)' }}>
          <div style={{ fontSize: '0.78rem', fontWeight: '600', color: 'var(--text-secondary)', marginBottom: '8px' }}>
            INFRASTRUCTURE COVERAGE
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '6px', fontSize: '0.75rem' }}>
            <div style={{ background: 'rgba(15, 23, 42, 0.5)', padding: '6px 10px', borderRadius: '4px', display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Wards:</span>
              <span style={{ fontWeight: '600' }}>{summary?.infrastructure.wards ?? 0}</span>
            </div>
            <div style={{ background: 'rgba(15, 23, 42, 0.5)', padding: '6px 10px', borderRadius: '4px', display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Grid Cells:</span>
              <span style={{ fontWeight: '600' }}>{summary?.infrastructure.grid_cells ?? 0}</span>
            </div>
            <div style={{ background: 'rgba(15, 23, 42, 0.5)', padding: '6px 10px', borderRadius: '4px', display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Road Segments:</span>
              <span style={{ fontWeight: '600' }}>{summary?.infrastructure.roads ?? 0}</span>
            </div>
            <div style={{ background: 'rgba(15, 23, 42, 0.5)', padding: '6px 10px', borderRadius: '4px', display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Bus Stops:</span>
              <span style={{ fontWeight: '600' }}>{summary?.infrastructure.bus_stops ?? 0}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
