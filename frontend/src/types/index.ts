// GeoJSON Types
export interface GeoJSONGeometry {
  type: string;
  coordinates: any;
}

export interface GeoJSONFeature<P = Record<string, any>> {
  type: "Feature";
  geometry: GeoJSONGeometry;
  properties: P;
}

export interface GeoJSONFeatureCollection<P = Record<string, any>> {
  type: "FeatureCollection";
  features: GeoJSONFeature<P>[];
}

// System & Dashboard Types
export interface SystemHealth {
  status: string;
  database: string;
  version: string;
}

export interface DashboardSummary {
  engine_name: string;
  timestamp: string;
  system_status: string;
  provenance_status: string;
  is_synthetic: boolean;
  scientific_validation_warning: string;
  infrastructure: {
    wards: number;
    grid_cells: number;
    roads: number;
    hospitals: number;
    police_stations: number;
    fire_stations: number;
    schools: number;
    bus_stops: number;
    bus_routes: number;
    water_bodies: number;
  };
  flood_risk: {
    total_evaluated_cells: number;
    by_category: Record<string, number>;
    high_risk_cells_count: number;
  };
  traffic: {
    monitored_segments: number;
    average_speed_kmh: number;
    congested_segments_count: number;
  };
  air_quality: {
    forecast_count: number;
    average_pollutant_value: number;
  };
  simulations: {
    total_runs: number;
    latest_run_id: string | null;
    latest_scenario: string | null;
  };
  optimization: {
    total_runs: number;
    latest_run_id: string | null;
    latest_method: string | null;
  };
}

export interface CityStateMetadata {
  engine_name: string;
  state_schema_version: string;
  spatial_reference: string;
  canonical_spatial_units: string[];
  active_grid_cells_count: number;
  active_wards_count: number;
  total_persisted_snapshots: number;
  latest_snapshot_created_at: string | null;
  data_sources: string[];
  is_synthetic: boolean;
  data_provenance_status: string;
  scientific_validation_warning: string;
}

// Flood Risk Types
export interface FloodRiskProperties {
  prediction_id: number;
  cell_id: number;
  cell_code: string;
  model_name: string;
  model_version: string;
  prediction_time: string;
  predicted_probability: number;
  predicted_class: "LOW" | "MEDIUM" | "HIGH" | "VERY HIGH";
  is_synthetic: boolean;
  data_provenance_status: string;
  scientific_validation_warning?: string;
  feature_importance_shap?: Record<string, number>;
  environmental_features?: {
    elevation_m?: number;
    slope_deg?: number;
    ndvi?: number;
    ndwi?: number;
    ndbi?: number;
    population_count?: number;
  };
}

// Traffic & GNN Types
export interface GNNTrafficProperties {
  prediction_id: number;
  road_id: number;
  osm_id?: number;
  name?: string;
  highway_type?: string;
  lanes?: number;
  maxspeed?: number;
  prediction_time: string;
  forecast_horizon_minutes: number;
  predicted_speed: number;
  predicted_congestion_ratio?: number;
  gnn_architecture: string;
  model_name: string;
  model_version: string;
  is_synthetic: boolean;
  data_provenance_status: string;
  scientific_validation_warning?: string;
}

// Air Quality Types
export interface AirQualityProperties {
  prediction_id: number;
  station_name: string;
  pollutant: string;
  forecast_issue_time: string;
  target_time: string;
  horizon_hours: number;
  predicted_value: number;
  aqi_sub_index?: number;
  model_name: string;
  model_version: string;
  is_synthetic: boolean;
  data_provenance_status: string;
  scientific_validation_warning?: string;
}

// Emergency Infrastructure Types
export interface HospitalProperties {
  id: number;
  osm_id?: number;
  name: string;
  beds?: number | null;
  created_at?: string;
}

export interface PoliceProperties {
  id: number;
  osm_id?: number;
  name: string;
  created_at?: string;
}

export interface FireStationProperties {
  id: number;
  osm_id?: number;
  name: string;
  created_at?: string;
}

export interface WardProperties {
  id: number;
  ward_number: number;
  ward_name: string;
  population?: number;
  area_sqkm?: number;
  created_at?: string;
}

export interface RoadProperties {
  id: number;
  osm_id?: number;
  name?: string;
  highway_type?: string;
  lanes?: number;
  maxspeed?: number;
}

export interface BuildingProperties {
  id: number;
  osm_id?: number;
  building_type?: string;
  height?: number | null;
  levels?: number | null;
  created_at?: string;
}

// Simulation Engine Types
export interface ScenarioTypeOption {
  type: string;
  name: string;
  description: string;
  parameter_schema: Record<string, any>;
}

export interface SimulationCreateRequest {
  scenario_type: string;
  parameters: Record<string, any>;
  base_timestamp?: string;
  simulation_timestamp?: string;
  spatial_scope?: Record<string, any>;
  save?: boolean;
}

export interface SimulationRunDetail {
  simulation_id: string;
  scenario_type: string;
  scenario_name: string;
  base_state_timestamp: string;
  simulation_timestamp: string;
  engine_version: string;
  is_synthetic: boolean;
  parameters: Record<string, any>;
  impact_summary: {
    severity_assessment?: string;
    affected_cells_count?: number;
    affected_roads_count?: number;
    overall_traffic_speed_delta_pct?: number;
    overall_flood_risk_delta_pct?: number;
    warnings?: string[];
    [key: string]: any;
  };
  provenance: Record<string, any>;
  transformations: any[];
  base_state_count: number;
  simulated_state_count: number;
  created_at?: string;
}

// Emergency Optimization Types
export interface EmergencyDemand {
  demand_id: string;
  location: { type: string; coordinates: [number, number] };
  demand_quantity: number;
  priority: number;
  hazard_type?: string;
  ward_id?: number;
}

export interface EmergencyResource {
  resource_id: string;
  resource_type: "hospital" | "police_station" | "fire_station";
  name: string;
  location: { type: string; coordinates: [number, number] };
  capacity: number;
  beds?: number;
}

export interface AllocationResult {
  demand_id: string;
  resource_id: string;
  resource_type: string;
  assigned_capacity: number;
  travel_time_minutes: number;
  travel_distance_km: number;
  hazard_penalty: number;
  total_weighted_cost: number;
  demand_location: [number, number];
  resource_location: [number, number];
}

export interface OptimizationRunDetail {
  run_id: string;
  simulation_id?: string;
  base_state_timestamp?: string;
  optimization_timestamp?: string;
  optimization_method: string;
  objective_function: string;
  engine_version: string;
  is_synthetic: boolean;
  constraints?: Record<string, any>;
  resource_types: string[];
  summary: {
    total_demand: number;
    served_demand: number;
    unserved_demand: number;
    total_travel_cost: number;
    average_travel_cost: number;
    demand_summary?: Record<string, any>;
    resource_summary?: Record<string, any>;
  };
  allocations: AllocationResult[];
  baseline_comparison?: {
    nearest_resource_total_cost?: number;
    cost_improvement_percentage?: number;
    unserved_demand_diff?: number;
  };
  impact_comparison?: Record<string, any>;
  provenance: Record<string, any>;
  created_at?: string;
}

export interface OptimizationCreatePayload {
  base_timestamp?: string;
  simulation_id?: string;
  resource_types: string[];
  method: "ortools_min_cost_flow" | "nearest_resource";
  save?: boolean;
}

// AI Interface Types
export interface AIQueryRequest {
  query: string;
  spatial_context?: string;
  simulation_id?: string;
}

export interface AIToolCall {
  tool: string;
  parameters: Record<string, any>;
}

export interface AIToolResult {
  tool: string;
  success: boolean;
  data?: any;
  error?: string;
}

export interface AIMapAction {
  action: string;
  layer?: string;
  visible?: boolean;
  bounds?: [number, number, number, number];
  center?: [number, number];
  zoom?: number;
  risk?: string;
}

export interface AIProvenance {
  data_sources: string[];
  model_type: string;
  timestamp: string;
  is_synthetic: boolean;
  scientific_validation_warning?: string;
}

export interface AIResponse {
  query_id: string;
  query: string;
  answer: string;
  intent: string;
  response_type: "text" | "table" | "chart" | "feature_list" | "map_action" | "simulation_result" | "optimization_result";
  tool_calls: AIToolCall[];
  tool_results: AIToolResult[];
  data?: Record<string, any>;
  map_actions: AIMapAction[];
  provenance: AIProvenance;
  warnings: string[];
  suggested_followups: string[];
  created_at: string;
}

