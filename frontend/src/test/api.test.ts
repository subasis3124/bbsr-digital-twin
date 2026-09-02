import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ApiService } from '../services/api';

describe('ApiService Client', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('fetches dashboard summary successfully', async () => {
    const mockSummary = {
      engine_name: 'Bhubaneswar Digital Twin Command Center',
      timestamp: '2026-09-02T20:00:00Z',
      system_status: 'OPERATIONAL',
      provenance_status: 'synthetic_fallback',
      is_synthetic: true,
      scientific_validation_warning: 'WARNING',
      infrastructure: {
        wards: 67,
        grid_cells: 50,
        roads: 120,
        hospitals: 10,
        police_stations: 8,
        fire_stations: 4,
        schools: 15,
        bus_stops: 30,
        bus_routes: 5,
        water_bodies: 12,
      },
      flood_risk: { total_evaluated_cells: 50, by_category: { LOW: 40, HIGH: 10 }, high_risk_cells_count: 10 },
      traffic: { monitored_segments: 120, average_speed_kmh: 32.5, congested_segments_count: 5 },
      air_quality: { forecast_count: 20, average_pollutant_value: 45.2 },
      simulations: { total_runs: 2, latest_run_id: null, latest_scenario: null },
      optimization: { total_runs: 1, latest_run_id: null, latest_method: null },
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockSummary,
    } as any);

    const res = await ApiService.getDashboardSummary();
    expect(res.engine_name).toBe('Bhubaneswar Digital Twin Command Center');
    expect(res.infrastructure.wards).toBe(67);
  });

  it('handles API errors gracefully', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      json: async () => ({ detail: 'Database connection failed' }),
    } as any);

    await expect(ApiService.getDashboardSummary()).rejects.toThrow('Database connection failed');
  });

  it('constructs correct query parameters for flood risk endpoint', async () => {
    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ type: 'FeatureCollection', features: [] }),
    } as any);
    global.fetch = fetchSpy;

    await ApiService.getFloodRisk({ risk_level: 'HIGH', limit: 50 });
    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/flood-risk?limit=50&risk_level=HIGH'),
      expect.any(Object)
    );
  });
});
