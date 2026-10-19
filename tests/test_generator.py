"""
test_generator.py — Unit testy pro modul generator.py

Ověřují, že generátor grafů produkuje grafy odpovídající zadaným parametrům.
Kritické pro validaci, že aplikace generuje korektní struktury.

Spuštění:  pytest tests/ -v
"""

import pytest
import networkx as nx

# ============================================================================
# TESTY: Generování grafů dle parametrů
# ============================================================================

class TestGraphGeneration:
    """
    Ověření, že vygenerovaný graf odpovídá zadaným parametrům.

    Kontroly:
    - Správný počet uzlů
    - Správný počet hran
    - Orientovanost / neorientovanost
    - Ohodnocenost a rozsah vah
    """

    def test_node_and_edge_count(self):
        from generator import generate_graph
        from models import GraphConfig
        config = GraphConfig(node_count=10, edge_count=15, directed=False,
                             weighted=True, weight_min=1, weight_max=10)
        result = generate_graph(config)
        G = result["graph"]
        seed = result["seed"]
        assert G.number_of_nodes() == 10
        assert G.number_of_edges() == 15

    def test_directed_graph(self):
        from generator import generate_graph
        from models import GraphConfig
        config = GraphConfig(node_count=10, edge_count=15, directed=True,
                             weighted=True, weight_min=1, weight_max=10)
        result = generate_graph(config)
        G = result["graph"]
        seed = result["seed"]
        assert G.is_directed() is True

    def test_weight_range(self):
        from generator import generate_graph
        from models import GraphConfig
        config = GraphConfig(node_count=10, edge_count=15, directed=False,
                             weighted=True, weight_min=5, weight_max=20)
        result = generate_graph(config)
        G = result["graph"]
        seed = result["seed"]
        for u, v, d in G.edges(data=True):
            assert 5 <= d["weight"] <= 20

    def test_unweighted_graph(self):
        from generator import generate_graph
        from models import GraphConfig
        config = GraphConfig(node_count=10, edge_count=15, directed=False,
                             weighted=False)
        result = generate_graph(config)
        G = result["graph"]
        seed = result["seed"]
        for u, v, d in G.edges(data=True):
            assert "weight" not in d or d["weight"] == 1


# ============================================================================
# TESTY: Strukturní vlastnosti generovaných grafů
# ============================================================================

class TestGraphStructuralProperties:
    """
    Ověření strukturních vlastností generovaných grafů.

    Kontroly:
    - Souvislost grafu (pokud je požadována)
    - Acyklický graf (DAG)
    - Bipartitní graf
    """

    def test_connected_graph(self):
        from generator import generate_graph
        from models import GraphConfig
        config = GraphConfig(node_count=10, edge_count=12, directed=False,
                             weighted=True, weight_min=1, weight_max=10,
                             connected=True)
        result = generate_graph(config)
        G = result["graph"]
        seed = result["seed"]
        assert nx.is_connected(G)

    def test_dag_generation(self):
        from generator import generate_graph
        from models import GraphConfig
        config = GraphConfig(node_count=10, edge_count=15, directed=True,
                             weighted=True, acyclic=True)
        result = generate_graph(config)
        G = result["graph"]
        seed = result["seed"]
        assert G.is_directed() is True
        assert nx.is_directed_acyclic_graph(G)

    def test_bipartite_generation(self):
        from generator import generate_graph
        from models import GraphConfig
        config = GraphConfig(node_count=10, edge_count=15, directed=False,
                             weighted=True, bipartite=True)
        result = generate_graph(config)
        G = result["graph"]
        seed = result["seed"]
        from networkx.algorithms import bipartite
        assert bipartite.is_bipartite(G)


# ============================================================================
# TESTY: Reprodukovatelnost (seed)
# ============================================================================

class TestReproducibility:
    """
    Ověření, že stejný seed generuje identický graf.
    Důležité pro opakované generování zadání.
    """

    def test_same_seed_same_graph(self):
        from generator import generate_graph
        from models import GraphConfig
        config = GraphConfig(node_count=10, edge_count=15, directed=False,
                             weighted=True, weight_min=1, weight_max=10)
        res1 = generate_graph(config)
        G1, seed1 = res1["graph"], res1["seed"]
        
        config.seed = seed1
        res2 = generate_graph(config)
        G2, seed2 = res2["graph"], res2["seed"]
        
        assert seed1 == seed2
        assert list(G1.edges(data=True)) == list(G2.edges(data=True))


# ============================================================================
# TESTY: Okrajové případy
# ============================================================================

class TestEdgeCases:
    """
    Testování limitních a okrajových hodnot.

    Kontroly:
    - Minimální graf (3 uzly, 2 hrany)
    - Velký graf (100+ uzlů)
    - Kompletní graf (maximální počet hran)
    - Nemožné parametry (příliš málo hran pro souvislost)
    """

    def test_minimal_graph(self):
        from generator import generate_graph
        from models import GraphConfig
        config = GraphConfig(node_count=3, edge_count=2, directed=False)
        result = generate_graph(config)
        G = result["graph"]
        seed = result["seed"]
        assert G.number_of_nodes() == 3
        assert G.number_of_edges() == 2

    def test_large_graph(self):
        from generator import generate_graph
        from models import GraphConfig
        config = GraphConfig(node_count=100, edge_count=200, directed=False)
        result = generate_graph(config)
        G = result["graph"]
        seed = result["seed"]
        assert G.number_of_nodes() == 100
        assert G.number_of_edges() == 200

    def test_complete_graph(self):
        from generator import generate_graph
        from models import GraphConfig
        config = GraphConfig(node_count=5, edge_count=10, directed=False)
        result = generate_graph(config)
        G = result["graph"]
        seed = result["seed"]
        assert G.number_of_nodes() == 5
        assert G.number_of_edges() == 10
