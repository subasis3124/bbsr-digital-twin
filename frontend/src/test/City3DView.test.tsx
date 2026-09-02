import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { City3DView } from '../components/Map/City3DView';

const mockActiveLayers = {
  terrain: true,
  buildings: true,
  floodRisk: true,
  trafficForecast: true,
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

describe('City3DView 3D GIS Visualization Suite', () => {
  it('renders graceful fallback when WebGL context is unavailable in test runner', () => {
    const onSwitch2D = vi.fn();

    render(
      <City3DView
        layers={mockActiveLayers}
        floodData={null}
        trafficData={null}
        airQualityData={null}
        hospitalsData={null}
        policeData={null}
        fireData={null}
        wardsData={null}
        roadsData={null}
        buildingsData={null}
        busStopsData={null}
        busRoutesData={null}
        waterBodiesData={null}
        activeSimulation={null}
        activeOptimization={null}
        onSelectEntity={vi.fn()}
        onSwitchTo2D={onSwitch2D}
      />
    );

    expect(screen.getByText('3D GIS Visualization Unavailable')).toBeInTheDocument();
    expect(screen.getByText('Return to 2D Command Center')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Return to 2D Command Center'));
    expect(onSwitch2D).toHaveBeenCalledTimes(1);
  });
});
