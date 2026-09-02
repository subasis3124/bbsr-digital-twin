import React, { useState } from 'react';
import { Route, Play, ShieldAlert, CheckCircle2, RotateCcw, AlertTriangle, Scale } from 'lucide-react';
import { ApiService } from '../../services/api';
import { OptimizationRunDetail, AllocationResult } from '../../types';
import { ProvenanceBadge } from '../Provenance/ProvenanceBadge';

interface EmergencyOptimizationPanelProps {
  onOptimizationRunComplete: (result: OptimizationRunDetail) => void;
  activeOptimization: OptimizationRunDetail | null;
  onClearOptimization: () => void;
  activeSimulationId?: string;
}

export const EmergencyOptimizationPanel: React.FC<EmergencyOptimizationPanelProps> = ({
  onOptimizationRunComplete,
  activeOptimization,
  onClearOptimization,
  activeSimulationId,
}) => {
  const [selectedResourceType, setSelectedResourceType] = useState<string>('hospital');
  const [method, setMethod] = useState<'ortools_min_cost_flow' | 'nearest_resource'>('ortools_min_cost_flow');
  const [running, setRunning] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleRunOptimization = async () => {
    try {
      setRunning(true);
      setError(null);

      const res = await ApiService.runEmergencyOptimization({
        resource_types: [selectedResourceType],
        method,
        simulation_id: activeSimulationId,
        save: true,
      });

      onOptimizationRunComplete(res);
    } catch (err: any) {
      setError(err.message || 'Optimization solver failed');
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="glass-panel">
      <div className="panel-header">
        <span className="panel-title">
          <Route size={16} color="var(--accent-teal)" />
          EMERGENCY OPTIMIZATION ENGINE
        </span>
        {activeOptimization && (
          <button
            className="btn-secondary"
            onClick={onClearOptimization}
            style={{ padding: '2px 6px', fontSize: '0.72rem' }}
          >
            <RotateCcw size={12} /> Reset Overlay
          </button>
        )}
      </div>

      <div className="panel-content" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
          Solves capacitated min-cost flow allocation of emergency demand incidents to available healthcare and emergency response facilities.
        </div>

        {activeSimulationId && (
          <div style={{ background: 'rgba(139, 92, 246, 0.15)', border: '1px solid rgba(139, 92, 246, 0.3)', padding: '6px 10px', borderRadius: '6px', fontSize: '0.75rem', color: '#c4b5fd' }}>
            Bound to Simulation Scenario: <strong>{activeSimulationId.slice(0, 8)}...</strong>
          </div>
        )}

        {error && (
          <div className="provenance-banner" style={{ background: 'rgba(239, 68, 68, 0.1)', borderColor: 'rgba(239, 68, 68, 0.3)', color: '#fca5a5' }}>
            <ShieldAlert size={16} />
            <div>{error}</div>
          </div>
        )}

        <div className="form-group">
          <label className="form-label">Target Infrastructure Category</label>
          <select
            className="form-select"
            value={selectedResourceType}
            onChange={(e) => setSelectedResourceType(e.target.value)}
            disabled={running}
          >
            <option value="hospital">Hospitals & Healthcare</option>
            <option value="police_station">Police Stations</option>
            <option value="fire_station">Fire Stations</option>
          </select>
        </div>

        <div className="form-group">
          <label className="form-label">Optimization Solver Method</label>
          <select
            className="form-select"
            value={method}
            onChange={(e) => setMethod(e.target.value as any)}
            disabled={running}
          >
            <option value="ortools_min_cost_flow">OR-Tools Min-Cost Capacitated Flow</option>
            <option value="nearest_resource">Nearest Resource Baseline Heuristic</option>
          </select>
        </div>

        <button
          className="btn-primary"
          onClick={handleRunOptimization}
          disabled={running}
          style={{ background: 'linear-gradient(135deg, #0d9488 0%, #0f766e 100%)', borderColor: 'rgba(20, 184, 166, 0.4)' }}
        >
          <Play size={15} />
          {running ? 'Solving Min-Cost Flow...' : 'Calculate Optimal Allocation'}
        </button>

        {/* Results view */}
        {activeOptimization && (
          <div style={{ marginTop: '10px', paddingTop: '10px', borderTop: '1px solid var(--border-card)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span style={{ fontSize: '0.78rem', fontWeight: '700', color: 'var(--accent-teal)' }}>
                OPTIMIZATION RECOMMENDATION
              </span>
              <span className="provenance-tag simulated">DECISION SUPPORT</span>
            </div>

            <div className="kpi-grid" style={{ marginBottom: '10px' }}>
              <div className="kpi-card">
                <div className="kpi-card-header">SERVED DEMAND</div>
                <div className="kpi-val" style={{ color: 'var(--accent-teal)' }}>
                  {activeOptimization.summary?.served_demand} / {activeOptimization.summary?.total_demand}
                </div>
                <div className="kpi-sub">
                  Unserved: {activeOptimization.summary?.unserved_demand}
                </div>
              </div>

              <div className="kpi-card">
                <div className="kpi-card-header">TOTAL TRAVEL COST</div>
                <div className="kpi-val">
                  {activeOptimization.summary?.total_travel_cost?.toFixed(1)} <span style={{ fontSize: '0.75rem' }}>min</span>
                </div>
                <div className="kpi-sub">
                  Avg: {activeOptimization.summary?.average_travel_cost?.toFixed(1)} min
                </div>
              </div>
            </div>

            {activeOptimization.baseline_comparison?.cost_improvement_percentage !== undefined && (
              <div style={{ background: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.3)', padding: '8px 10px', borderRadius: '6px', fontSize: '0.78rem', color: '#6ee7b7', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Scale size={16} />
                <div>
                  <strong>+{activeOptimization.baseline_comparison.cost_improvement_percentage}% Improvement</strong> over Nearest-Resource Baseline
                </div>
              </div>
            )}

            {/* Allocation List */}
            <div style={{ fontSize: '0.75rem', fontWeight: '600', color: 'var(--text-secondary)', marginBottom: '6px' }}>
              ALLOCATION DIRECTORY ({activeOptimization.allocations?.length || 0})
            </div>
            <div style={{ maxHeight: '140px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {(activeOptimization.allocations || []).map((alloc: AllocationResult, idx: number) => (
                <div key={idx} style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '6px 8px', borderRadius: '4px', fontSize: '0.72rem', display: 'flex', justifyContent: 'space-between' }}>
                  <span>{alloc.demand_id} → {alloc.resource_id}</span>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-teal)' }}>
                    {alloc.travel_time_minutes?.toFixed(1)} min ({alloc.assigned_capacity} cap)
                  </span>
                </div>
              ))}
            </div>

            <ProvenanceBadge
              status="simulated"
              isSynthetic={true}
              warning="Optimization recommendations are decision-support outputs and do not represent actual dispatched units."
              sourceModel={`OR-Tools Flow Engine v${activeOptimization.engine_version}`}
            />
          </div>
        )}
      </div>
    </div>
  );
};
