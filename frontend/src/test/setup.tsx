import '@testing-library/jest-dom/vitest';
import React from 'react';
import { vi } from 'vitest';

// Mock Leaflet as DOM environment in tests doesn't support canvas/webgl map rendering
vi.mock('react-leaflet', () => ({
  MapContainer: ({ children }: any) => <div data-testid="map-container">{children}</div>,
  TileLayer: () => <div data-testid="tile-layer" />,
  GeoJSON: ({ data }: any) => <div data-testid="geojson-layer" data-features={data?.features?.length || 0} />,
  CircleMarker: ({ children }: any) => <div data-testid="circle-marker">{children}</div>,
  Polyline: () => <div data-testid="polyline-layer" />,
  Popup: ({ children }: any) => <div data-testid="popup">{children}</div>,
  Marker: () => <div data-testid="marker" />,
}));
