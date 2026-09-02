import React from 'react';
import { Clock } from 'lucide-react';

interface TimeControllerProps {
  selectedHorizon: number; // minutes
  onHorizonChange: (minutes: number) => void;
  stateMode: 'CURRENT' | 'FORECAST' | 'SIMULATED';
  onStateModeChange: (mode: 'CURRENT' | 'FORECAST' | 'SIMULATED') => void;
}

export const TimeController: React.FC<TimeControllerProps> = ({
  selectedHorizon,
  onHorizonChange,
  stateMode,
  onStateModeChange,
}) => {
  const horizons = [
    { label: 'Now (0m)', value: 0 },
    { label: '+15m', value: 15 },
    { label: '+30m', value: 30 },
    { label: '+60m', value: 60 },
  ];

  return (
    <div
      className="glass-panel"
      style={{
        padding: '8px 12px',
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '12px',
        maxWidth: '460px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        <Clock size={15} color="var(--accent-cyan)" />
        <span style={{ fontSize: '0.78rem', fontWeight: '600', color: 'var(--text-secondary)' }}>
          MODE:
        </span>
        <div className="nav-tab-group" style={{ padding: '2px' }}>
          <button
            className={`nav-tab-btn ${stateMode === 'CURRENT' ? 'active' : ''}`}
            onClick={() => onStateModeChange('CURRENT')}
            style={{ padding: '3px 8px', fontSize: '0.72rem' }}
          >
            Observed
          </button>
          <button
            className={`nav-tab-btn ${stateMode === 'FORECAST' ? 'active' : ''}`}
            onClick={() => onStateModeChange('FORECAST')}
            style={{ padding: '3px 8px', fontSize: '0.72rem' }}
          >
            Forecast
          </button>
          <button
            className={`nav-tab-btn ${stateMode === 'SIMULATED' ? 'active' : ''}`}
            onClick={() => onStateModeChange('SIMULATED')}
            style={{ padding: '3px 8px', fontSize: '0.72rem' }}
          >
            Counterfactual
          </button>
        </div>
      </div>

      {stateMode === 'FORECAST' && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Horizon:</span>
          <select
            className="form-select"
            value={selectedHorizon}
            onChange={(e) => onHorizonChange(Number(e.target.value))}
            style={{ padding: '2px 6px', fontSize: '0.75rem', height: '26px' }}
          >
            {horizons.map((h) => (
              <option key={h.value} value={h.value}>
                {h.label}
              </option>
            ))}
          </select>
        </div>
      )}
    </div>
  );
};
