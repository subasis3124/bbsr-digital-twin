import React from 'react';
import { ShieldAlert, Database } from 'lucide-react';

interface ProvenanceBadgeProps {
  status?: string; // 'synthetic_fallback' | 'validated_model' | 'counterfactual' | 'forecast'
  isSynthetic?: boolean;
  warning?: string;
  sourceModel?: string;
  compact?: boolean;
}

export const ProvenanceBadge: React.FC<ProvenanceBadgeProps> = ({
  status = 'synthetic_fallback',
  isSynthetic = true,
  warning,
  sourceModel,
  compact = false
}) => {
  const getBadgeType = () => {
    if (status === 'counterfactual' || status === 'simulated') return 'simulated';
    if (status === 'forecast') return 'forecast';
    if (isSynthetic || status === 'synthetic_fallback') return 'synthetic';
    return 'observed';
  };

  const badgeType = getBadgeType();

  if (compact) {
    return (
      <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
        <span className={`provenance-tag ${badgeType}`}>
          {badgeType.toUpperCase()}
        </span>
        {sourceModel && (
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            [{sourceModel}]
          </span>
        )}
      </div>
    );
  }

  return (
    <div style={{ margin: '8px 0' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
        <span className={`provenance-tag ${badgeType}`}>
          <Database size={11} /> {badgeType.toUpperCase()} STATE
        </span>
        {sourceModel && (
          <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
            Model: {sourceModel}
          </span>
        )}
      </div>

      {warning && (
        <div className="provenance-banner">
          <ShieldAlert size={16} style={{ flexShrink: 0, marginTop: '2px', color: 'var(--accent-amber)' }} />
          <div>
            <strong>Scientific Integrity Warning:</strong> {warning}
          </div>
        </div>
      )}
    </div>
  );
};
