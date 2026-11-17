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

    def test_didactic_options(self):
        from generator import generate_graph
        from models import GraphConfig

        # 1. Test unique weights (jednoznačné váhy pro MST)
        cfg_unique = GraphConfig(node_count=6, edge_count=8, directed=False, weighted=True,
                                 unique_weights=True, weight_min=1, weight_max=10, seed=42)
        res_unique = generate_graph(cfg_unique)
        weights = [data["weight"] for _, _, data in res_unique["graph"].edges(data=True)]
        assert len(weights) == len(set(weights)), "Váhy hran musí být navzájem unikátní!"

        # 2. Test force_bridge (garantovaný most a artikulace)
        cfg_bridge = GraphConfig(node_count=8, edge_count=10, directed=False, weighted=True,
                                 connected=True, force_bridge=True, seed=42)
        res_bridge = generate_graph(cfg_bridge)
        G_bridge = res_bridge["graph"]
        bridges = list(nx.bridges(G_bridge))
        articulations = list(nx.articulation_points(G_bridge))
        assert len(bridges) >= 1, "Graf musí obsahovat alespoň jeden most!"
        assert len(articulations) >= 1, "Graf musí obsahovat alespoň jednu artikulaci!"

        # 3. Test allow_negative_edge (bez záporného cyklu)
        cfg_neg = GraphConfig(node_count=6, edge_count=9, directed=True, weighted=True,
                              connected=True, allow_negative_edge=True, seed=42)
        res_neg = generate_graph(cfg_neg)
        G_neg = res_neg["graph"]
        neg_weights = [d["weight"] for _, _, d in G_neg.edges(data=True) if d["weight"] < 0]
        assert len(neg_weights) >= 1, "Graf musí obsahovat zápornou hranu pro Bellman-Ford!"
        assert not nx.negative_edge_cycle(G_neg), "Graf nesmí obsahovat záporný cyklus!"

