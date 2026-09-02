import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { TopHeader } from '../components/Header/TopHeader';
import { CityKPIPanel } from '../components/KPIPanel/CityKPIPanel';
import { ProvenanceBadge } from '../components/Provenance/ProvenanceBadge';
import { LayerControl } from '../components/Layers/LayerControl';
import { SpatialInspector } from '../components/SpatialInspector/SpatialInspector';
import { EmergencyOptimizationPanel } from '../components/Optimization/EmergencyOptimizationPanel';

const mockSummary = {
  engine_name: 'Bhubaneswar Digital Twin Command Center',
  timestamp: '2026-09-02T20:00:00Z',
  system_status: 'OPERATIONAL',
  provenance_status: 'synthetic_fallback',
  is_synthetic: true,
  scientific_validation_warning: 'WARNING: Synthetic validation data active.',
  infrastructure: {
    wards: 67,
    grid_cells: 100,
    roads: 250,
    hospitals: 12,
    police_stations: 8,
    fire_stations: 4,
    schools: 20,
    bus_stops: 45,
    bus_routes: 6,
    water_bodies: 15,
  },
  flood_risk: { total_evaluated_cells: 100, by_category: { LOW: 80, HIGH: 20 }, high_risk_cells_count: 20 },
  traffic: { monitored_segments: 250, average_speed_kmh: 34.2, congested_segments_count: 8 },
  air_quality: { forecast_count: 30, average_pollutant_value: 48.5 },
  simulations: { total_runs: 3, latest_run_id: null, latest_scenario: null },
  optimization: { total_runs: 2, latest_run_id: null, latest_method: null },
};

describe('Command Center Components Suite', () => {
  it('renders TopHeader with branding and synthetic warning badge', () => {
    render(<TopHeader summary={mockSummary} loading={false} onRefresh={vi.fn()} />);

    expect(screen.getByText('BHUBANESWAR DIGITAL TWIN')).toBeInTheDocument();
    expect(screen.getByText('COMMAND-CENTER v1.0')).toBeInTheDocument();
    expect(screen.getByText('SYNTHETIC FALLBACK')).toBeInTheDocument();
    expect(screen.getByText('OPERATIONAL')).toBeInTheDocument();
  });

  it('renders CityKPIPanel with derived metric indicators', () => {
    render(<CityKPIPanel summary={mockSummary} loading={false} />);

    expect(screen.getByText('CITY STATE OVERVIEW')).toBeInTheDocument();
    expect(screen.getByText('20')).toBeInTheDocument(); // High risk count
    expect(screen.getByText(/34.2/)).toBeInTheDocument(); // Avg traffic speed
    expect(screen.getByText(/48.5/)).toBeInTheDocument(); // AQI
  });

  it('displays scientific integrity provenance warning banner', () => {
    render(
      <ProvenanceBadge
        status="synthetic_fallback"
        isSynthetic={true}
        warning="Synthetic baseline data in use."
      />
    );

    expect(screen.getByText('SYNTHETIC STATE')).toBeInTheDocument();
    expect(screen.getByText(/Synthetic baseline data in use/)).toBeInTheDocument();
  });

  it('handles layer toggling in LayerControl', () => {
    const onToggle = vi.fn();
    const activeLayers = {
      terrain: true,
      buildings: true,
      floodRisk: true,
      trafficForecast: false,
      airQuality: true,
      hospitals: true,
      policeStations: false,
      fireStations: false,
      wards: true,
      roads: false,
      busStops: false,
      busRoutes: false,
      waterBodies: false,
      allocations: true,
    };

    render(<LayerControl layers={activeLayers} onToggleLayer={onToggle} />);

    fireEvent.click(screen.getByText('Traffic Forecast (GNN)'));
    expect(onToggle).toHaveBeenCalledWith('trafficForecast');
  });

  it('renders "Capacity unavailable" in SpatialInspector when capacity is missing', () => {
    const mockResourceEntity = {
      type: 'resource' as const,
      id: 1,
      data: {
        name: 'AIIMS Bhubaneswar',
        beds: null, // Unknown capacity
        resource_type: 'hospital',
      },
    };

    render(<SpatialInspector selectedEntity={mockResourceEntity} onClose={vi.fn()} />);

    expect(screen.getByText('AIIMS Bhubaneswar')).toBeInTheDocument();
    expect(screen.getByText('Capacity unavailable')).toBeInTheDocument();
  });

  it('renders optimization results cleanly in EmergencyOptimizationPanel', () => {
    const mockOptResult = {
      run_id: 'test-run-uuid',
      optimization_method: 'ortools_min_cost_flow',
      objective_function: 'min_cost_flow',
      engine_version: '1.0.0',
      is_synthetic: true,
      resource_types: ['hospital'],
      summary: {
        total_demand: 10,
        served_demand: 10,
        unserved_demand: 0,
        total_travel_cost: 45.2,
        average_travel_cost: 4.5,
      },
      allocations: [
        {
          demand_id: 'dem-1',
          resource_id: 'hosp-1',
          resource_type: 'hospital',
          assigned_capacity: 1,
          travel_time_minutes: 4.5,
          travel_distance_km: 2.2,
          hazard_penalty: 0,
          total_weighted_cost: 4.5,
          demand_location: [85.82, 20.29] as [number, number],
          resource_location: [85.83, 20.30] as [number, number],
        },
      ],
      baseline_comparison: {
        cost_improvement_percentage: 18.5,
      },
      provenance: {},
    };

    render(
      <EmergencyOptimizationPanel
        onOptimizationRunComplete={vi.fn()}
        activeOptimization={mockOptResult}
        onClearOptimization={vi.fn()}
      />
    );

    expect(screen.getByText('OPTIMIZATION RECOMMENDATION')).toBeInTheDocument();
    expect(screen.getByText(/18.5% Improvement/)).toBeInTheDocument();
    expect(screen.getByText(/10 \/ 10/)).toBeInTheDocument();
  });
});
