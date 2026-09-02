import {
  DashboardSummary,
  CityStateMetadata,
  GeoJSONFeatureCollection,
  GeoJSONFeature,
  FloodRiskProperties,
  GNNTrafficProperties,
  AirQualityProperties,
  BuildingProperties,
  ScenarioTypeOption,
  SimulationCreateRequest,
  SimulationRunDetail,
  OptimizationCreatePayload,
  OptimizationRunDetail,
  EmergencyResource,
  AIQueryRequest,
  AIResponse
} from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const errBody = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errBody.detail || `HTTP Error ${res.status}: ${res.statusText}`);
  }

  return res.json();
}

export const ApiService = {
  // 1. Dashboard Summary
  async getDashboardSummary(): Promise<DashboardSummary> {
    return fetchJson<DashboardSummary>(`${API_BASE}/dashboard/summary`);
  },

  // 2. City State Metadata & Features
  async getCityStateMetadata(): Promise<CityStateMetadata> {
    return fetchJson<CityStateMetadata>(`${API_BASE}/city-state/metadata`);
  },

  async getCityStates(params?: {
    spatial_unit_type?: string;
    state_type?: string;
    forecast_horizon_minutes?: number;
    limit?: number;
  }): Promise<GeoJSONFeatureCollection> {
    const q = new URLSearchParams();
    if (params?.spatial_unit_type) q.append('spatial_unit_type', params.spatial_unit_type);
    if (params?.state_type) q.append('state_type', params.state_type);
    if (params?.forecast_horizon_minutes !== undefined) q.append('forecast_horizon_minutes', params.forecast_horizon_minutes.toString());
    if (params?.limit) q.append('limit', params.limit.toString());
    return fetchJson<GeoJSONFeatureCollection>(`${API_BASE}/city-state?${q.toString()}`);
  },

  // 3. Flood Risk
  async getFloodRisk(params?: {
    limit?: number;
    risk_level?: string;
    min_lon?: number;
    min_lat?: number;
    max_lon?: number;
    max_lat?: number;
  }): Promise<GeoJSONFeatureCollection<FloodRiskProperties>> {
    const q = new URLSearchParams();
    if (params?.limit) q.append('limit', params.limit.toString());
    if (params?.risk_level) q.append('risk_level', params.risk_level);
    if (params?.min_lon !== undefined && params?.max_lon !== undefined) {
      q.append('min_lon', params.min_lon.toString());
      q.append('min_lat', params.min_lat!.toString());
      q.append('max_lon', params.max_lon.toString());
      q.append('max_lat', params.max_lat!.toString());
    }
    return fetchJson<GeoJSONFeatureCollection<FloodRiskProperties>>(`${API_BASE}/flood-risk?${q.toString()}`);
  },

  async getFloodRiskById(predictionId: number): Promise<GeoJSONFeature<FloodRiskProperties>> {
    return fetchJson<GeoJSONFeature<FloodRiskProperties>>(`${API_BASE}/flood-risk/${predictionId}`);
  },

  // 4. Traffic & GNN
  async getGNNTraffic(params?: {
    limit?: number;
    forecast_horizon_minutes?: number;
    road_id?: number;
  }): Promise<GeoJSONFeatureCollection<GNNTrafficProperties>> {
    const q = new URLSearchParams();
    if (params?.limit) q.append('limit', params.limit.toString());
    if (params?.forecast_horizon_minutes !== undefined) q.append('forecast_horizon_minutes', params.forecast_horizon_minutes.toString());
    if (params?.road_id) q.append('road_id', params.road_id.toString());
    return fetchJson<GeoJSONFeatureCollection<GNNTrafficProperties>>(`${API_BASE}/gnn/traffic?${q.toString()}`);
  },

  // 5. Air Quality
  async getAirQuality(params?: {
    limit?: number;
    pollutant?: string;
    horizon_hours?: number;
  }): Promise<GeoJSONFeatureCollection<AirQualityProperties>> {
    const q = new URLSearchParams();
    if (params?.limit) q.append('limit', params.limit.toString());
    if (params?.pollutant) q.append('pollutant', params.pollutant);
    if (params?.horizon_hours) q.append('horizon_hours', params.horizon_hours.toString());
    return fetchJson<GeoJSONFeatureCollection<AirQualityProperties>>(`${API_BASE}/air-quality?${q.toString()}`);
  },

  // 6. Infrastructure Entities
  async getHospitals(limit = 200): Promise<GeoJSONFeatureCollection> {
    return fetchJson<GeoJSONFeatureCollection>(`${API_BASE}/hospitals?limit=${limit}`);
  },

  async getPoliceStations(limit = 200): Promise<GeoJSONFeatureCollection> {
    return fetchJson<GeoJSONFeatureCollection>(`${API_BASE}/police?limit=${limit}`);
  },

  async getFireStations(limit = 200): Promise<GeoJSONFeatureCollection> {
    return fetchJson<GeoJSONFeatureCollection>(`${API_BASE}/fire-stations?limit=${limit}`);
  },

  async getWards(limit = 100): Promise<GeoJSONFeatureCollection> {
    return fetchJson<GeoJSONFeatureCollection>(`${API_BASE}/wards?limit=${limit}`);
  },

  async getRoads(limit = 300): Promise<GeoJSONFeatureCollection> {
    return fetchJson<GeoJSONFeatureCollection>(`${API_BASE}/roads?limit=${limit}`);
  },

  async getBusStops(limit = 200): Promise<GeoJSONFeatureCollection> {
    return fetchJson<GeoJSONFeatureCollection>(`${API_BASE}/bus-stops?limit=${limit}`);
  },

  async getBusRoutes(limit = 50): Promise<GeoJSONFeatureCollection> {
    return fetchJson<GeoJSONFeatureCollection>(`${API_BASE}/bus-routes?limit=${limit}`);
  },

  async getWaterBodies(limit = 100): Promise<GeoJSONFeatureCollection> {
    return fetchJson<GeoJSONFeatureCollection>(`${API_BASE}/water-bodies?limit=${limit}`);
  },

  async getBuildings(limit = 300, wardId?: number): Promise<GeoJSONFeatureCollection<BuildingProperties>> {
    const q = new URLSearchParams();
    q.append('limit', limit.toString());
    if (wardId !== undefined) q.append('ward_id', wardId.toString());
    return fetchJson<GeoJSONFeatureCollection<BuildingProperties>>(`${API_BASE}/buildings?${q.toString()}`);
  },

  // 7. Simulation API
  async getScenarioTypes(): Promise<{ scenario_types?: ScenarioTypeOption[]; scenarios?: ScenarioTypeOption[]; scientific_validation_warning?: string }> {
    return fetchJson(`${API_BASE}/simulations/scenarios/types`);
  },

  async createSimulation(req: SimulationCreateRequest): Promise<SimulationRunDetail> {
    return fetchJson<SimulationRunDetail>(`${API_BASE}/simulations`, {
      method: 'POST',
      body: JSON.stringify(req),
    });
  },

  async listSimulations(limit = 20): Promise<{ total: number; items: any[] }> {
    return fetchJson(`${API_BASE}/simulations?limit=${limit}`);
  },

  async getSimulationDetail(simulationId: string): Promise<SimulationRunDetail> {
    return fetchJson<SimulationRunDetail>(`${API_BASE}/simulations/${simulationId}`);
  },

  // 8. Emergency Optimization API
  async runEmergencyOptimization(payload: OptimizationCreatePayload): Promise<OptimizationRunDetail> {
    return fetchJson<OptimizationRunDetail>(`${API_BASE}/optimization/emergency`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async listOptimizationRuns(limit = 20): Promise<{ total: number; items: any[] }> {
    return fetchJson(`${API_BASE}/optimization/emergency?limit=${limit}`);
  },

  async getOptimizationDetail(runId: string): Promise<OptimizationRunDetail> {
    return fetchJson<OptimizationRunDetail>(`${API_BASE}/optimization/emergency/${runId}`);
  },

  async getAvailableEmergencyResources(): Promise<{ total_resources: number; resources: EmergencyResource[] }> {
    return fetchJson(`${API_BASE}/optimization/resources`);
  },

  // 9. Natural Language AI Interface API
  async sendAIQuery(req: AIQueryRequest): Promise<AIResponse> {
    return fetchJson<AIResponse>(`${API_BASE}/ai/query`, {
      method: 'POST',
      body: JSON.stringify(req),
    });
  },

  async fetchAITools(): Promise<{ total_tools: number; tools: any[] }> {
    return fetchJson(`${API_BASE}/ai/tools`);
  },

  async fetchAIIntents(): Promise<{ intents: string[] }> {
    return fetchJson(`${API_BASE}/ai/intents`);
  }
};
