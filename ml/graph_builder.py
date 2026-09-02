import torch
import numpy as np
import pandas as pd
import networkx as nx
from typing import Dict, List, Tuple, Any, Optional
from sqlalchemy.orm import Session
from shapely.geometry import shape, LineString, MultiLineString
from geoalchemy2.shape import to_shape

from backend.app.models import Road

class UrbanGraphBuilder:
    """
    Constructs a spatial road network graph for Bhubaneswar from PostGIS Road geometries.
    Nodes represent road segments (identified by DB road_id).
    Edges represent physical connectivity/adjacency between road segments.
    """

    def __init__(self, db: Optional[Session] = None):
        self.db = db

    def load_roads(self) -> List[Dict[str, Any]]:
        """
        Loads road entities from PostGIS database into a structured list.
        """
        if not self.db:
            return []
        
        roads = self.db.query(Road).all()
        road_records = []
        for r in roads:
            geom_obj = to_shape(r.geom) if r.geom is not None else None
            road_records.append({
                "road_id": r.id,
                "osm_id": float(r.osm_id) if r.osm_id else 0.0,
                "name": r.name or f"Road_{r.id}",
                "highway_type": r.highway_type or "residential",
                "lanes": r.lanes or 1,
                "maxspeed": float(r.maxspeed or 40),
                "oneway": bool(r.oneway) if r.oneway is not None else False,
                "geom": geom_obj
            })
        return road_records

    def build_graph(
        self,
        road_records: Optional[List[Dict[str, Any]]] = None,
        distance_threshold_meters: float = 0.0005,  # ~50 meters in lat/lon degrees
        add_self_loops: bool = True
    ) -> Dict[str, Any]:
        """
        Builds graph topology (nodes, edge_index, edge_attr, mappings, and statistics).
        If road_records is not provided, loads roads from database session.
        """
        if road_records is None:
            road_records = self.load_roads()

        if not road_records:
            # Fallback for empty graph handling
            return {
                "x": torch.empty((0, 0), dtype=torch.float32),
                "edge_index": torch.empty((2, 0), dtype=torch.long),
                "edge_attr": torch.empty((0, 1), dtype=torch.float32),
                "road_to_idx": {},
                "idx_to_road": {},
                "num_nodes": 0,
                "num_edges": 0,
                "statistics": {
                    "num_nodes": 0,
                    "num_edges": 0,
                    "num_connected_components": 0,
                    "num_isolated_nodes": 0,
                    "average_degree": 0.0,
                    "density": 0.0
                }
            }

        # 1. Deterministic Node Index Mapping
        # Sort road_records by road_id for strict reproducibility
        sorted_roads = sorted(road_records, key=lambda r: r["road_id"])
        num_nodes = len(sorted_roads)
        
        road_to_idx: Dict[int, int] = {}
        idx_to_road: Dict[int, int] = {}
        
        for idx, r in enumerate(sorted_roads):
            rid = r["road_id"]
            road_to_idx[rid] = idx
            idx_to_road[idx] = rid

        # 2. Construct Edge Topology & Geometry Adjacency
        edges: List[Tuple[int, int]] = []
        edge_weights: List[float] = []

        # Convert geometries and compute bounding boxes / distances
        geoms = [r.get("geom") for r in sorted_roads]

        for i in range(num_nodes):
            geom_i = geoms[i]
            oneway_i = sorted_roads[i].get("oneway", False)
            
            for j in range(i + 1, num_nodes):
                geom_j = geoms[j]
                
                # Check spatial connectivity
                connected = False
                dist = 0.0
                
                if geom_i is not None and geom_j is not None:
                    if geom_i.intersects(geom_j) or geom_i.touches(geom_j):
                        connected = True
                        dist = 0.0
                    else:
                        d = geom_i.distance(geom_j)
                        if d <= distance_threshold_meters:
                            connected = True
                            dist = d
                else:
                    # Fallback topological adjacency if geometry missing
                    connected = (i == j - 1)
                    dist = 0.0001

                if connected:
                    weight = max(1.0, 1.0 / (1.0 + dist * 1000.0))
                    
                    # Add edge (i -> j)
                    edges.append((i, j))
                    edge_weights.append(weight)
                    
                    # Add reverse edge (j -> i) if not oneway or for undirected graph propagation
                    if not oneway_i:
                        edges.append((j, i))
                        edge_weights.append(weight)

        # 3. Handle Self-Loops
        if add_self_loops:
            existing_self_loops = set((u, v) for u, v in edges if u == v)
            for i in range(num_nodes):
                if (i, i) not in existing_self_loops:
                    edges.append((i, i))
                    edge_weights.append(1.0)

        # Build PyTorch Tensors
        if edges:
            edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous() # [2, E]
            edge_attr = torch.tensor(edge_weights, dtype=torch.float32).unsqueeze(-1) # [E, 1]
        else:
            edge_index = torch.empty((2, 0), dtype=torch.long)
            edge_attr = torch.empty((0, 1), dtype=torch.float32)

        # 4. NetworkX Graph Analysis & Graph Statistics
        nx_graph = nx.Graph()
        nx_graph.add_nodes_from(range(num_nodes))
        nx_edges = [(u, v) for u, v in edges if u != v]
        nx_graph.add_edges_from(nx_edges)

        num_edges = edge_index.size(1)
        num_components = nx.number_connected_components(nx_graph) if num_nodes > 0 else 0
        degrees = dict(nx_graph.degree())
        isolated_nodes = sum(1 for deg in degrees.values() if deg == 0)
        avg_degree = float(np.mean(list(degrees.values()))) if degrees else 0.0
        density = float(nx.density(nx_graph)) if num_nodes > 1 else 0.0

        stats = {
            "num_nodes": num_nodes,
            "num_edges": num_edges,
            "num_connected_components": num_components,
            "num_isolated_nodes": isolated_nodes,
            "average_degree": round(avg_degree, 4),
            "density": round(density, 6)
        }

        # 5. Extract Static Node Feature Tensor
        # Static features per node: [length_estimate, maxspeed_norm, lanes_norm, centroid_lon, centroid_lat, degree]
        static_features = []
        for idx in range(num_nodes):
            r = sorted_roads[idx]
            g = r.get("geom")
            
            length = float(g.length) if g else 0.01
            centroid_lon = float(g.centroid.x) if g else 85.8246
            centroid_lat = float(g.centroid.y) if g else 20.2961
            
            lanes = float(r.get("lanes", 1)) / 4.0
            maxspeed = float(r.get("maxspeed", 40)) / 100.0
            degree_norm = float(degrees.get(idx, 0)) / 10.0
            
            static_features.append([
                length,
                maxspeed,
                lanes,
                centroid_lon,
                centroid_lat,
                degree_norm
            ])

        x_static = torch.tensor(static_features, dtype=torch.float32) if static_features else torch.empty((0, 6), dtype=torch.float32)

        return {
            "x_static": x_static,
            "edge_index": edge_index,
            "edge_attr": edge_attr,
            "road_to_idx": road_to_idx,
            "idx_to_road": idx_to_road,
            "num_nodes": num_nodes,
            "num_edges": num_edges,
            "roads": sorted_roads,
            "statistics": stats
        }
