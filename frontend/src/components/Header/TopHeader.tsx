import React from 'react';
import { Activity, ShieldAlert, Cpu, RefreshCw, CheckCircle2, AlertTriangle, Map, Box } from 'lucide-react';
import { DashboardSummary } from '../../types';

interface TopHeaderProps {
  summary: DashboardSummary | null;
  loading: boolean;
  onRefresh: () => void;
  viewMode?: '2D' | '3D';
  onViewModeChange?: (mode: '2D' | '3D') => void;
}

export const TopHeader: React.FC<TopHeaderProps> = ({
  summary,
  loading,
  onRefresh,
  viewMode = '2D',
  onViewModeChange,
}) => {
  const formattedTime = summary?.timestamp
    ? new Date(summary.timestamp).toUTCString()
    : new Date().toUTCString();

  return (
    <header className="top-header">
      <div className="brand-container">
        <Cpu className="brand-logo-icon" size={24} />
        <div>
          <span className="brand-title">BHUBANESWAR DIGITAL TWIN</span>
          <span className="brand-subtitle" style={{ marginLeft: '10px' }}>
            COMMAND-CENTER v1.0
          </span>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        {/* 2D / 3D Mode Selector Toggle */}
        {onViewModeChange && (
          <div
            style={{
              display: 'flex',
              background: 'rgba(15, 23, 42, 0.8)',
              padding: '3px',
              borderRadius: '8px',
              border: '1px solid var(--border-card)',
              gap: '4px',
            }}
          >
            <button
              className={`nav-tab-btn ${viewMode === '2D' ? 'active' : ''}`}
              onClick={() => onViewModeChange('2D')}
              style={{
                padding: '4px 10px',
                fontSize: '0.78rem',
                borderRadius: '6px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                background: viewMode === '2D' ? 'var(--accent-cyan)' : 'transparent',
                color: viewMode === '2D' ? '#0f172a' : 'var(--text-secondary)',
                fontWeight: viewMode === '2D' ? '700' : '500',
              }}
            >
              <Map size={14} /> 2D MAP
            </button>
            <button
              className={`nav-tab-btn ${viewMode === '3D' ? 'active' : ''}`}
              onClick={() => onViewModeChange('3D')}
              style={{
                padding: '4px 10px',
                fontSize: '0.78rem',
                borderRadius: '6px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                background: viewMode === '3D' ? 'var(--accent-cyan)' : 'transparent',
                color: viewMode === '3D' ? '#0f172a' : 'var(--text-secondary)',
                fontWeight: viewMode === '3D' ? '700' : '500',
              }}
            >
              <Box size={14} /> 3D CITY
            </button>
          </div>
        )}

        <div className="header-meta">
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-secondary)' }}>
            <Activity size={15} color="var(--accent-cyan)" />
            <span style={{ fontFamily: 'var(--font-mono)' }}>{formattedTime}</span>
          </div>

          {summary?.is_synthetic && (
            <div
              className="status-badge warning"
              title="System relies on synthetic integration data baselines"
            >
              <AlertTriangle size={13} />
              <span>SYNTHETIC FALLBACK</span>
            </div>
          )}

          <div className="status-badge operational">
            <span className="pulse-dot"></span>
            <span>{summary?.system_status || 'OPERATIONAL'}</span>
          </div>

          <button
            className="btn-secondary"
            onClick={onRefresh}
            disabled={loading}
            style={{ padding: '4px 8px', fontSize: '0.75rem' }}
            title="Refresh City State Data"
          >
            <RefreshCw size={13} className={loading ? 'pulse-dot' : ''} />
            <span>Sync</span>
          </button>
        </div>
      </div>
    </header>
  );
};
