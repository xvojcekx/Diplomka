"""
models.py — Pydantic modely pro request/response
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class GraphConfig(BaseModel):
    """Konfigurace pro generování jednoho grafu."""
    node_count: int = Field(ge=3, le=500, description="Počet uzlů")
    edge_count: int = Field(ge=2, le=10000, description="Počet hran")
    directed: bool = Field(default=False, description="Orientovaný graf")
    weighted: bool = Field(default=True, description="Ohodnocený")
    weight_min: int = Field(default=1, description="Minimální váha")
    weight_max: int = Field(default=10, description="Maximální váha")
    connected: bool = Field(default=True, description="Zaručeně souvislý")
    acyclic: bool = Field(default=False, description="Acyklický (DAG / strom)")
    bipartite: bool = Field(default=False, description="Bipartitní")
    seed: Optional[int] = Field(default=None, description="Seed pro reprodukovatelnost")


class BatchConfig(BaseModel):
    """Konfigurace pro generování sady grafů."""
    batch_size: int = Field(ge=1, le=50, default=1, description="Počet sad")
    node_min: int = Field(ge=3, le=500, default=5, description="Min uzlů")
    node_max: int = Field(ge=3, le=500, default=10, description="Max uzlů")
    edge_min: int = Field(ge=2, le=10000, default=6, description="Min hran")
    edge_max: int = Field(ge=2, le=10000, default=15, description="Max hran")
    directed: bool = False
    weighted: bool = True
    weight_min: int = 1
    weight_max: int = 10
    connected: bool = True
    acyclic: bool = False
    bipartite: bool = False
    seed: Optional[int] = None
    # Algoritmy k výpočtu
    algo_shortest_path: bool = True
    algo_mst: bool = True
    algo_topological: bool = False
    algo_bipartite: bool = False


class GraphResult(BaseModel):
    """Výsledek generování jednoho grafu."""
    graph_id: str
    config: GraphConfig
    properties: dict
    algorithms: dict
    adjacency_matrix: List[List[float]]
    edge_list: List[dict]
    png_path: Optional[str] = None
    interactive_path: Optional[str] = None
