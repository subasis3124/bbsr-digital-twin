import React, { useState, useEffect } from 'react';
import { Sliders, Play, AlertOctagon, CheckCircle2, ShieldAlert, RotateCcw } from 'lucide-react';
import { ApiService } from '../../services/api';
import { SimulationRunDetail, ScenarioTypeOption } from '../../types';
import { ProvenanceBadge } from '../Provenance/ProvenanceBadge';

interface WhatIfPanelProps {
  onSimulationRunComplete: (result: SimulationRunDetail) => void;
  activeSimulation: SimulationRunDetail | null;
  onClearSimulation: () => void;
}

export const WhatIfPanel: React.FC<WhatIfPanelProps> = ({
  onSimulationRunComplete,
  activeSimulation,
  onClearSimulation,
}) => {
  const [scenarios, setScenarios] = useState<ScenarioTypeOption[]>([]);
  const [selectedScenarioType, setSelectedScenarioType] = useState<string>('heavy_rainfall');
  const [loading, setLoading] = useState<boolean>(false);
  const [running, setRunning] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Form states for parameters
  const [rainfallMultiplier, setRainfallMultiplier] = useState<number>(1.5);
  const [rainfallDelta, setRainfallDelta] = useState<number>(50.0);

  const [closedRoadIdsStr, setClosedRoadIdsStr] = useState<string>('1, 2');
  const [closureDuration, setClosureDuration] = useState<number>(4.0);

  const [pollutant, setPollutant] = useState<string>('pm25');
  const [pollutionMultiplier, setPollutionMultiplier] = useState<number>(2.0);

  const [hospitalDemandMult, setHospitalDemandMult] = useState<number>(2.0);
  const [incidentSurge, setIncidentSurge] = useState<number>(10);

  useEffect(() => {
    async function loadScenarios() {
      try {
        setLoading(true);
        const res = await ApiService.getScenarioTypes();
        const scList = res.scenarios || res.scenario_types || [];
        setScenarios(scList);
      } catch (err: any) {
        console.error('Failed to load simulation scenario types', err);
      } finally {
        setLoading(false);
      }
    }
    loadScenarios();
  }, []);

  const handleRunSimulation = async () => {
    try {
      setRunning(true);
      setError(null);

      let parameters: Record<string, any> = {};

      if (selectedScenarioType === 'heavy_rainfall') {
        parameters = {
          rainfall_multiplier: Number(rainfallMultiplier),
          rainfall_delta_mm: Number(rainfallDelta),
          duration_hours: 2.0,
        };
      } else if (selectedScenarioType === 'road_closure') {
        const roadIds = closedRoadIdsStr
          .split(',')
          .map((s) => parseInt(s.trim()))
          .filter((n) => !isNaN(n));
        parameters = {
          closed_road_ids: roadIds.length > 0 ? roadIds : [1],
          closure_duration_hours: Number(closureDuration),
          rerouting_capacity_factor: 0.5,
        };
      } else if (selectedScenarioType === 'air_pollution') {
        parameters = {
          pollutant,
          multiplier: Number(pollutionMultiplier),
          delta: 0.0,
        };
      } else if (selectedScenarioType === 'emergency_demand') {
        parameters = {
          hospital_demand_multiplier: Number(hospitalDemandMult),
          incident_count_surge: Number(incidentSurge),
        };
      }

      const res = await ApiService.createSimulation({
        scenario_type: selectedScenarioType,
        parameters,
        save: true,
      });

      onSimulationRunComplete(res);
    } catch (err: any) {
      setError(err.message || 'Simulation execution failed');
    } finally {
      setRunning(false);
    }
  };

  const currentScenario = scenarios.find((s) => s.type === selectedScenarioType);

  return (
    <div className="glass-panel">
      <div className="panel-header">
        <span className="panel-title">
          <Sliders size={16} color="var(--accent-purple)" />
          WHAT-IF SIMULATION ENGINE
        </span>
        {activeSimulation && (
          <button
            className="btn-secondary"
            onClick={onClearSimulation}
            style={{ padding: '2px 6px', fontSize: '0.72rem' }}
          >
            <RotateCcw size={12} /> Clear Impact
          </button>
        )}
      </div>

      <div className="panel-content" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
          Configure counterfactual perturbations to model stress response across flood, traffic, and healthcare infrastructure.
        </div>

        {error && (
          <div className="provenance-banner" style={{ background: 'rgba(239, 68, 68, 0.1)', borderColor: 'rgba(239, 68, 68, 0.3)', color: '#fca5a5' }}>
            <ShieldAlert size={16} />
            <div>{error}</div>
          </div>
        )}

        <div className="form-group">
          <label className="form-label">Select Simulation Scenario</label>
          <select
            className="form-select"
            value={selectedScenarioType}
            onChange={(e) => setSelectedScenarioType(e.target.value)}
            disabled={running}
          >
            <option value="heavy_rainfall">Heavy Rainfall Simulation</option>
            <option value="road_closure">Road Network Closure</option>
            <option value="air_pollution">Air Pollution Surge</option>
            <option value="emergency_demand">Emergency Demand Surge</option>
          </select>
        </div>

        {currentScenario && (
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', background: 'rgba(15, 23, 42, 0.6)', padding: '8px', borderRadius: '6px' }}>
            {currentScenario.description}
          </div>
        )}

        {/* Dynamic Parameter Forms */}
        <div style={{ background: 'rgba(15, 23, 42, 0.4)', padding: '10px', borderRadius: '8px', border: '1px solid var(--border-card)' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: '600', color: 'var(--accent-purple)', marginBottom: '8px' }}>
            SCENARIO PARAMETERS
          </div>

          {selectedScenarioType === 'heavy_rainfall' && (
            <>
              <div className="form-group">
                <label className="form-label">Rainfall Multiplier ({rainfallMultiplier}x)</label>
                <input
                  type="range"
                  min="0.5"
                  max="5.0"
                  step="0.1"
                  value={rainfallMultiplier}
                  onChange={(e) => setRainfallMultiplier(Number(e.target.value))}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Precipitation Delta (mm)</label>
                <input
                  type="number"
                  className="form-input"
                  value={rainfallDelta}
                  onChange={(e) => setRainfallDelta(Number(e.target.value))}
                />
              </div>
            </>
          )}

          {selectedScenarioType === 'road_closure' && (
            <>
              <div className="form-group">
                <label className="form-label">Closed Road IDs (Comma-separated)</label>
                <input
                  type="text"
                  className="form-input"
                  value={closedRoadIdsStr}
                  onChange={(e) => setClosedRoadIdsStr(e.target.value)}
                  placeholder="e.g. 1, 2, 5"
                />
              </div>
              <div className="form-group">
                <label className="form-label">Closure Duration (Hours)</label>
                <input
                  type="number"
                  className="form-input"
                  value={closureDuration}
                  onChange={(e) => setClosureDuration(Number(e.target.value))}
                />
              </div>
            </>
          )}

          {selectedScenarioType === 'air_pollution' && (
            <>
              <div className="form-group">
                <label className="form-label">Target Pollutant</label>
                <select className="form-select" value={pollutant} onChange={(e) => setPollutant(e.target.value)}>
                  <option value="pm25">PM2.5</option>
                  <option value="pm10">PM10</option>
                  <option value="no2">NO2</option>
                  <option value="so2">SO2</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Surge Multiplier ({pollutionMultiplier}x)</label>
                <input
                  type="range"
                  min="1.0"
                  max="10.0"
                  step="0.5"
                  value={pollutionMultiplier}
                  onChange={(e) => setPollutionMultiplier(Number(e.target.value))}
                />
              </div>
            </>
          )}

          {selectedScenarioType === 'emergency_demand' && (
            <>
              <div className="form-group">
                <label className="form-label">Hospital Demand Multiplier ({hospitalDemandMult}x)</label>
                <input
                  type="range"
                  min="1.0"
                  max="5.0"
                  step="0.2"
                  value={hospitalDemandMult}
                  onChange={(e) => setHospitalDemandMult(Number(e.target.value))}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Incident Surge Count</label>
                <input
                  type="number"
                  className="form-input"
                  value={incidentSurge}
                  onChange={(e) => setIncidentSurge(Number(e.target.value))}
                />
              </div>
            </>
          )}
        </div>

        <button
          className="btn-primary"
          onClick={handleRunSimulation}
          disabled={running}
          style={{ background: 'linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%)', borderColor: 'rgba(139, 92, 246, 0.4)' }}
        >
          <Play size={15} />
          {running ? 'Running Counterfactual Simulation...' : 'Execute What-If Simulation'}
        </button>

        {/* Results display if active simulation present */}
        {activeSimulation && (
          <div style={{ marginTop: '10px', paddingTop: '10px', borderTop: '1px solid var(--border-card)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
              <span style={{ fontSize: '0.78rem', fontWeight: '700', color: 'var(--accent-purple)' }}>
                MODELED IMPACT SUMMARY
              </span>
              <span className="provenance-tag simulated">COUNTERFACTUAL</span>
            </div>

            <div style={{ background: 'rgba(139, 92, 246, 0.1)', padding: '10px', borderRadius: '6px', fontSize: '0.78rem', display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div>
                <strong>Severity Assessment:</strong> {activeSimulation.impact_summary?.severity_assessment || 'MODERATE'}
              </div>
              <div>
                <strong>Affected Spatial Units:</strong> {activeSimulation.impact_summary?.affected_cells_count ?? activeSimulation.simulated_state_count}
              </div>
              {activeSimulation.impact_summary?.overall_traffic_speed_delta_pct !== undefined && (
                <div>
                  <strong>Traffic Speed Impact:</strong>{' '}
                  <span style={{ color: 'var(--accent-rose)' }}>
                    {activeSimulation.impact_summary.overall_traffic_speed_delta_pct}%
                  </span>
                </div>
              )}
              {activeSimulation.impact_summary?.overall_flood_risk_delta_pct !== undefined && (
                <div>
                  <strong>Flood Risk Escalation:</strong>{' '}
                  <span style={{ color: 'var(--accent-rose)' }}>
                    +{activeSimulation.impact_summary.overall_flood_risk_delta_pct}%
                  </span>
                </div>
              )}
            </div>

            <ProvenanceBadge
              status="simulated"
              isSynthetic={true}
              warning="Scenario simulation predictions are decision-support counterfactual outputs."
              sourceModel={`WhatIfEngine v${activeSimulation.engine_version}`}
            />
          </div>
        )}
      </div>
    </div>
  );
};
