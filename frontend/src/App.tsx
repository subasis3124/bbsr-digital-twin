import React, { useState, useEffect } from 'react';
import { Activity, Layers, Sliders, Route, Eye, ShieldAlert } from 'lucide-react';
import { ApiService } from './services/api';
import {
  DashboardSummary,
  GeoJSONFeatureCollection,
  FloodRiskProperties,
  GNNTrafficProperties,
  AirQualityProperties,
  BuildingProperties,
  SimulationRunDetail,
  OptimizationRunDetail,
} from './types';
import { TopHeader } from './components/Header/TopHeader';
import { CityKPIPanel } from './components/KPIPanel/CityKPIPanel';
import { LayerControl, ActiveLayers } from './components/Layers/LayerControl';
import { WhatIfPanel } from './components/Simulation/WhatIfPanel';
import { EmergencyOptimizationPanel } from './components/Optimization/EmergencyOptimizationPanel';
import { TimeController } from './components/TimeControls/TimeController';
import { SpatialInspector } from './components/SpatialInspector/SpatialInspector';
import { CommandMap } from './components/Map/CommandMap';
import { City3DView } from './components/Map/City3DView';
import { NaturalLanguagePanel } from './components/NaturalLanguagePanel';
import { AIMapAction } from './types';

type SidebarTab = 'overview' | 'layers' | 'simulation' | 'optimization';

export const App: React.FC = () => {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loadingSummary, setLoadingSummary] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<SidebarTab>('overview');

  // Visualization View Mode (2D Map vs 3D City View)
  const [viewMode, setViewMode] = useState<'2D' | '3D'>('2D');

  // Layer Toggles
  const [layers, setLayers] = useState<ActiveLayers>({
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
  });

  // Layer Datasets
  const [floodData, setFloodData] = useState<GeoJSONFeatureCollection<FloodRiskProperties> | null>(null);
  const [trafficData, setTrafficData] = useState<GeoJSONFeatureCollection<GNNTrafficProperties> | null>(null);
  const [airQualityData, setAirQualityData] = useState<GeoJSONFeatureCollection<AirQualityProperties> | null>(null);
  const [hospitalsData, setHospitalsData] = useState<GeoJSONFeatureCollection | null>(null);
  const [policeData, setPoliceData] = useState<GeoJSONFeatureCollection | null>(null);
  const [fireData, setFireData] = useState<GeoJSONFeatureCollection | null>(null);
  const [wardsData, setWardsData] = useState<GeoJSONFeatureCollection | null>(null);
  const [roadsData, setRoadsData] = useState<GeoJSONFeatureCollection | null>(null);
  const [buildingsData, setBuildingsData] = useState<GeoJSONFeatureCollection<BuildingProperties> | null>(null);
  const [busStopsData, setBusStopsData] = useState<GeoJSONFeatureCollection | null>(null);
  const [busRoutesData, setBusRoutesData] = useState<GeoJSONFeatureCollection | null>(null);
  const [waterBodiesData, setWaterBodiesData] = useState<GeoJSONFeatureCollection | null>(null);

  // Time & Temporal State
  const [forecastHorizon, setForecastHorizon] = useState<number>(0);
  const [stateMode, setStateMode] = useState<'CURRENT' | 'FORECAST' | 'SIMULATED'>('CURRENT');

  // Simulation & Optimization State
  const [activeSimulation, setActiveSimulation] = useState<SimulationRunDetail | null>(null);
  const [activeOptimization, setActiveOptimization] = useState<OptimizationRunDetail | null>(null);

  // AI Assistant Panel State
  const [isAIPanelOpen, setIsAIPanelOpen] = useState<boolean>(true);

  // Inspector Selection
  const [selectedEntity, setSelectedEntity] = useState<{
    type: 'ward' | 'road' | 'resource' | 'flood_cell' | 'air_quality' | 'building';
    id: string | number;
    data: Record<string, any>;
  } | null>(null);

  const handleDispatchMapAction = (action: AIMapAction) => {
    if (action.action === 'set_layer_visibility' && action.layer) {
      setLayers((prev) => ({
        ...prev,
        [action.layer as keyof ActiveLayers]: action.visible ?? true,
      }));
    }
  };

  // Fetch Summary
  const loadSummary = async () => {
    try {
      setLoadingSummary(true);
      const data = await ApiService.getDashboardSummary();
      setSummary(data);
    } catch (err) {
      console.error('Failed to load dashboard summary', err);
    } finally {
      setLoadingSummary(false);
    }
  };

  useEffect(() => {
    loadSummary();
  }, []);

  // Fetch Active Layer Data dynamically
  useEffect(() => {
    if (layers.floodRisk && !floodData) {
      ApiService.getFloodRisk({ limit: 200 }).then(setFloodData).catch(console.error);
    }
    if (layers.trafficForecast && !trafficData) {
      ApiService.getGNNTraffic({ limit: 200, forecast_horizon_minutes: forecastHorizon }).then(setTrafficData).catch(console.error);
    }
    if (layers.airQuality && !airQualityData) {
      ApiService.getAirQuality({ limit: 100 }).then(setAirQualityData).catch(console.error);
    }
    if (layers.hospitals && !hospitalsData) {
      ApiService.getHospitals(100).then(setHospitalsData).catch(console.error);
    }
    if (layers.policeStations && !policeData) {
      ApiService.getPoliceStations(100).then(setPoliceData).catch(console.error);
    }
    if (layers.fireStations && !fireData) {
      ApiService.getFireStations(100).then(setFireData).catch(console.error);
    }
    if (layers.wards && !wardsData) {
      ApiService.getWards(100).then(setWardsData).catch(console.error);
    }
    if (layers.roads && !roadsData) {
      ApiService.getRoads(200).then(setRoadsData).catch(console.error);
    }
    if (layers.buildings && !buildingsData) {
      ApiService.getBuildings(300).then(setBuildingsData).catch(console.error);
    }
    if (layers.busStops && !busStopsData) {
      ApiService.getBusStops(100).then(setBusStopsData).catch(console.error);
    }
    if (layers.busRoutes && !busRoutesData) {
      ApiService.getBusRoutes(50).then(setBusRoutesData).catch(console.error);
    }
    if (layers.waterBodies && !waterBodiesData) {
      ApiService.getWaterBodies(100).then(setWaterBodiesData).catch(console.error);
    }
  }, [layers, forecastHorizon]);

  const handleToggleLayer = (layerKey: keyof ActiveLayers) => {
    setLayers((prev) => ({ ...prev, [layerKey]: !prev[layerKey] }));
  };

  const handleSimulationRunComplete = (res: SimulationRunDetail) => {
    setActiveSimulation(res);
    setStateMode('SIMULATED');
    loadSummary();
  };

  const handleOptimizationRunComplete = (res: OptimizationRunDetail) => {
    setActiveOptimization(res);
    setLayers((prev) => ({ ...prev, allocations: true }));
    loadSummary();
  };

  return (
    <div className="app-container">
      {/* Top Header with 2D/3D Mode Switcher */}
      <TopHeader
        summary={summary}
        loading={loadingSummary}
        onRefresh={loadSummary}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
      />

      {/* Main Workspace Grid */}
      <main className="dashboard-main">
        {/* Left Sidebar */}
        <aside className="left-sidebar">
          {/* Module Navigation Tabs */}
          <div className="nav-tab-group">
            <button
              className={`nav-tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
              onClick={() => setActiveTab('overview')}
            >
              <Activity size={14} /> Overview
            </button>
            <button
              className={`nav-tab-btn ${activeTab === 'layers' ? 'active' : ''}`}
              onClick={() => setActiveTab('layers')}
            >
              <Layers size={14} /> Layers
            </button>
            <button
              className={`nav-tab-btn ${activeTab === 'simulation' ? 'active' : ''}`}
              onClick={() => setActiveTab('simulation')}
            >
              <Sliders size={14} /> What-If
            </button>
            <button
              className={`nav-tab-btn ${activeTab === 'optimization' ? 'active' : ''}`}
              onClick={() => setActiveTab('optimization')}
            >
              <Route size={14} /> Opt
            </button>
          </div>

          {/* Active Tab Panel Content */}
          {activeTab === 'overview' && <CityKPIPanel summary={summary} loading={loadingSummary} />}
          {activeTab === 'layers' && <LayerControl layers={layers} onToggleLayer={handleToggleLayer} />}
          {activeTab === 'simulation' && (
            <WhatIfPanel
              onSimulationRunComplete={handleSimulationRunComplete}
              activeSimulation={activeSimulation}
              onClearSimulation={() => setActiveSimulation(null)}
            />
          )}
          {activeTab === 'optimization' && (
            <EmergencyOptimizationPanel
              onOptimizationRunComplete={handleOptimizationRunComplete}
              activeOptimization={activeOptimization}
              onClearOptimization={() => setActiveOptimization(null)}
              activeSimulationId={activeSimulation?.simulation_id}
            />
          )}
        </aside>

        {/* Center Primary Map Area */}
        <div className="map-view-container">
          {/* Floating Time Controls & AI Assistant Button Header */}
          <div className="map-floating-left flex gap-2 items-center">
            <TimeController
              selectedHorizon={forecastHorizon}
              onHorizonChange={setForecastHorizon}
              stateMode={stateMode}
              onStateModeChange={setStateMode}
            />
            <button
              onClick={() => setIsAIPanelOpen((prev) => !prev)}
              className={`px-3 py-1.5 rounded-lg border text-xs font-semibold shadow-lg transition-all flex items-center gap-1.5 ${
                isAIPanelOpen
                  ? 'bg-cyan-600 border-cyan-400 text-white shadow-cyan-900/50'
                  : 'bg-slate-900/90 hover:bg-slate-800 border-slate-700 text-cyan-400'
              }`}
              title="Toggle Natural Language AI Assistant"
              id="toggle-ai-panel-btn"
            >
              <span>🤖</span>
              <span>AI Assistant</span>
            </button>
          </div>

          {viewMode === '2D' ? (
            <CommandMap
              layers={layers}
              floodData={floodData}
              trafficData={trafficData}
              airQualityData={airQualityData}
              hospitalsData={hospitalsData}
              policeData={policeData}
              fireData={fireData}
              wardsData={wardsData}
              roadsData={roadsData}
              busStopsData={busStopsData}
              busRoutesData={busRoutesData}
              waterBodiesData={waterBodiesData}
              activeOptimization={activeOptimization}
              onSelectEntity={setSelectedEntity}
            />
          ) : (
            <City3DView
              layers={layers}
              floodData={floodData}
              trafficData={trafficData}
              airQualityData={airQualityData}
              hospitalsData={hospitalsData}
              policeData={policeData}
              fireData={fireData}
              wardsData={wardsData}
              roadsData={roadsData}
              buildingsData={buildingsData}
              busStopsData={busStopsData}
              busRoutesData={busRoutesData}
              waterBodiesData={waterBodiesData}
              activeSimulation={activeSimulation}
              activeOptimization={activeOptimization}
              onSelectEntity={setSelectedEntity}
              onSwitchTo2D={() => setViewMode('2D')}
            />
          )}

          {/* Natural Language AI Assistant Overlay Panel */}
          <NaturalLanguagePanel
            isOpen={isAIPanelOpen}
            onClose={() => setIsAIPanelOpen(false)}
            onDispatchMapAction={handleDispatchMapAction}
            activeSpatialContext={selectedEntity ? `${selectedEntity.type}:${selectedEntity.id}` : undefined}
            activeSimulationId={activeSimulation?.simulation_id}
          />
        </div>

        {/* Right Sidebar Drawer */}
        <aside className="right-sidebar">
          <SpatialInspector
            selectedEntity={selectedEntity}
            onClose={() => setSelectedEntity(null)}
          />
        </aside>
      </main>
    </div>
  );
};

export default App;
