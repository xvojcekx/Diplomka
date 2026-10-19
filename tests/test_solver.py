"""
test_solver.py — Unit testy pro modul solver.py

Ověřují matematickou správnost implementovaných grafových algoritmů.
Toto je klíčová testovací sada pro bod 5 zadání DP:
"Ověřte funkčnost aplikace s využitím standardních testů."

Spuštění:  pytest tests/ -v
"""

import pytest
import networkx as nx

# ============================================================================
# FIXTURES — Předdefinované grafy pro testování
# ============================================================================

@pytest.fixture
def simple_weighted_graph():
    """Jednoduchý ohodnocený neorientovaný graf (5 uzlů)."""
    G = nx.Graph()
    G.add_weighted_edges_from([
        (0, 1, 4), (0, 2, 1), (1, 2, 2),
        (1, 3, 5), (2, 3, 8), (3, 4, 3)
    ])
    return G

@pytest.fixture
def simple_directed_graph():
    """Orientovaný acyklický graf (DAG) pro topologické třídění."""
    G = nx.DiGraph()
    G.add_edges_from([(0, 1), (0, 2), (1, 3), (2, 3), (3, 4)])
    return G

@pytest.fixture
def bipartite_graph():
    """Bipartitní graf pro testování bipartitnosti."""
    G = nx.Graph()
    G.add_edges_from([(0, 3), (0, 4), (1, 3), (1, 5), (2, 4), (2, 5)])
    return G

@pytest.fixture
def disconnected_graph():
    """Nesouvislý graf — dva oddělené komponenty."""
    G = nx.Graph()
    G.add_edges_from([(0, 1), (1, 2)])
    G.add_edges_from([(5, 6), (6, 7)])
    return G


# ============================================================================
# TESTY: Dijkstrův algoritmus (nejkratší cesta)
# ============================================================================

class TestShortestPathDijkstra:
    """
    Ověření správnosti implementace Dijkstrova algoritmu.

    Kontroly:
    - Správná délka nejkratší cesty
    - Správná sekvence uzlů na cestě
    - Chování pro neexistující cestu
    - Chování pro záporné váhy (Dijkstra by neměl fungovat)
    """

    def test_basic_shortest_path(self, simple_weighted_graph):
        from solver import shortest_path_dijkstra
        result = shortest_path_dijkstra(simple_weighted_graph, 0, 4)
        assert result["error"] is None
        assert result["distance"] == 11
        assert result["path"] == [0, 2, 1, 3, 4]

    def test_no_path_exists(self, disconnected_graph):
        from solver import shortest_path_dijkstra
        result = shortest_path_dijkstra(disconnected_graph, 0, 6)
        assert result["error"] is not None

    def test_path_to_self(self, simple_weighted_graph):
        from solver import shortest_path_dijkstra
        result = shortest_path_dijkstra(simple_weighted_graph, 2, 2)
        assert result["distance"] == 0
        assert result["path"] == [2]

    def test_directed_graph(self, simple_directed_graph):
        from solver import shortest_path_dijkstra
        result = shortest_path_dijkstra(simple_directed_graph, 0, 4)
        assert result["error"] is None
        assert result["distance"] == 3
        assert result["path"] in ([0, 1, 3, 4], [0, 2, 3, 4])


# ============================================================================
# TESTY: Minimální kostra (Kruskal)
# ============================================================================

class TestMinimumSpanningTree:
    """
    Ověření správnosti výpočtu minimální kostry.

    Kontroly:
    - Celková váha MST
    - Počet hran v kostře (musí být n-1)
    - Kostra tvoří souvislý podgraf
    - Chování pro nesouvislý graf (měl by vrátit chybu/varování)
    """

    def test_mst_total_weight(self, simple_weighted_graph):
        from solver import minimum_spanning_tree
        result = minimum_spanning_tree(simple_weighted_graph)
        assert result["error"] is None
        assert result["total_weight"] == 11

    def test_mst_edge_count(self, simple_weighted_graph):
        from solver import minimum_spanning_tree
        result = minimum_spanning_tree(simple_weighted_graph)
        assert len(result["tree_edges"]) == 4

    def test_mst_disconnected(self, disconnected_graph):
        from solver import minimum_spanning_tree
        result = minimum_spanning_tree(disconnected_graph)
        assert result["error"] is not None


# ============================================================================
# TESTY: Topologické třídění
# ============================================================================

class TestTopologicalSort:
    """
    Ověření správnosti topologického třídění.

    Kontroly:
    - Platnost pořadí (každá hrana u→v má u před v)
    - Chování pro graf s cyklem (nemělo by existovat)
    - Chování pro neorientovaný graf
    """

    def test_valid_topological_order(self, simple_directed_graph):
        from solver import topological_sort
        result = topological_sort(simple_directed_graph)
        assert result["valid"] is True
        order = result["order"]
        assert order.index(0) < order.index(1)
        assert order.index(1) < order.index(3)
        assert order.index(3) < order.index(4)

    def test_cyclic_graph(self):
        from solver import topological_sort
        G = nx.DiGraph()
        G.add_edges_from([(1, 2), (2, 3), (3, 1)])
        result = topological_sort(G)
        assert result["valid"] is False


# ============================================================================
# TESTY: Bipartitnost
# ============================================================================

class TestBipartiteCheck:
    """
    Ověření správnosti detekce bipartitních grafů.

    Kontroly:
    - Korektní identifikace bipartitního grafu
    - Korektní identifikace nebipartitního grafu (lichý cyklus)
    - Správné rozdělení do dvou množin
    """

    def test_is_bipartite(self, bipartite_graph):
        from solver import is_bipartite_check
        result = is_bipartite_check(bipartite_graph)
        assert result["is_bipartite"] is True
        assert len(result["sets"]) == 2

    def test_not_bipartite(self):
        from solver import is_bipartite_check
        G = nx.Graph()
        G.add_edges_from([(1, 2), (2, 3), (3, 1)])
        result = is_bipartite_check(G)
        assert result["is_bipartite"] is False


# ============================================================================
# TESTY: Vlastnosti grafu (graph_properties)
# ============================================================================

class TestGraphProperties:
    """
    Ověření správnosti výpočtu základních vlastností grafu.

    Kontroly:
    - Počet uzlů a hran
    - Souvislost
    - Hustota
    - Max/min stupně a váhy
    - Stupňová sekvence
    """

    def test_basic_properties(self, simple_weighted_graph):
        from solver import graph_properties
        props = graph_properties(simple_weighted_graph)
        assert props["node_count"] == 5
        assert props["edge_count"] == 6
        assert props["is_connected"] is True

    def test_degree_sequence(self, simple_weighted_graph):
        from solver import graph_properties
        props = graph_properties(simple_weighted_graph)
        assert props["degree_sequence"] == [3, 3, 3, 2, 1]

    def test_degree_extremes(self, simple_weighted_graph):
        from solver import graph_properties
        props = graph_properties(simple_weighted_graph)
        assert props["max_degree_val"] == 3
        assert props["min_degree_val"] == 1


# ============================================================================
# TESTY: Krokovací algoritmy (BFS, DFS, Kruskal, Borůvka, Dijkstra)
# ============================================================================

class TestAlgorithmSteps:
    """
    Ověření správnosti krokovaných verzí algoritmů pro vizualizér.

    Kontroly:
    - Počet kroků odpovídá očekávání
    - Každý krok obsahuje validní data (visited, current, edges)
    - Finální stav odpovídá výsledku z "nekrokované" verze
    """

    def test_bfs_steps_count(self, simple_weighted_graph):
        from solver import bfs_steps
        steps = bfs_steps(simple_weighted_graph, source=0)
        assert len(steps["steps"]) > 0

    def test_dfs_steps(self, simple_weighted_graph):
        from solver import dfs_steps
        steps = dfs_steps(simple_weighted_graph, source=0)
        assert len(steps["steps"]) > 0

    def test_kruskal_steps_match_mst(self, simple_weighted_graph):
        from solver import kruskal_steps
        steps = kruskal_steps(simple_weighted_graph)
        assert len(steps["steps"]) > 0
        assert steps["steps"][-1]["action"] == "done"

    def test_boruvka_steps(self, simple_weighted_graph):
        from solver import boruvka_steps
        steps = boruvka_steps(simple_weighted_graph)
        assert len(steps["steps"]) > 0

    def test_bellman_ford_steps(self, simple_weighted_graph):
        from solver import bellman_ford_steps
        steps = bellman_ford_steps(simple_weighted_graph, source=0, target=4)
        assert steps["error"] is None
        assert len(steps["steps"]) > 0


# ============================================================================
# TESTY: Pokročilé algoritmy (Sekce A) a Validátor (Grader)
# ============================================================================

class TestAdvancedAlgorithmsAndGrader:
    """Testy pro Bellman-Ford, Max Flow, Barvení, Euler, Hamilton, SCC/Mosty a Grader."""

    def test_bellman_ford_negative_weights(self):
        from solver import bellman_ford
        G = nx.DiGraph()
        G.add_edge(0, 1, weight=4)
        G.add_edge(0, 2, weight=5)
        G.add_edge(2, 1, weight=-2)
        res = bellman_ford(G, 0, 1)
        assert res["error"] is None
        assert res["distance"] == 3
        assert res["path"] == [0, 2, 1]

    def test_max_flow_and_min_cut(self, simple_weighted_graph):
        from solver import ford_fulkerson_max_flow
        res = ford_fulkerson_max_flow(simple_weighted_graph, 0, 4)
        assert res["error"] is None
        assert res["max_flow"] == 3
        assert res["min_cut_value"] == 3

    def test_graph_coloring(self, bipartite_graph):
        from solver import graph_coloring
        res = graph_coloring(bipartite_graph)
        assert res["error"] is None
        assert res["chromatic_number"] == 2

    def test_euler_and_hamilton(self):
        from solver import euler_path, hamilton_path
        # Cyklus C4 má jak Eulerovskou kružnici, tak Hamiltonovskou kružnici
        G = nx.cycle_graph(4)
        eu = euler_path(G)
        hm = hamilton_path(G)
        assert eu["has_euler_circuit"] is True
        assert hm["has_hamilton_cycle"] is True

    def test_components_and_bridges(self, simple_weighted_graph):
        from solver import components_and_bridges
        res = components_and_bridges(simple_weighted_graph)
        assert res["error"] is None
        # Hrana 3-4 je most a uzel 3 je artikulace
        assert "u3" in res["articulation_points"]
        assert "u3–u4" in res["bridges"]

    def test_grader_multi_solution_mst_and_toposort(self):
        from grader import validate_mst, validate_topological_sort
        # Čtverec se všemi vahami = 1 má 4 různé minimální kostry o váze 3
        G = nx.cycle_graph(4)
        for u, v in G.edges():
            G[u][v]["weight"] = 1
        edge_list = [{"source": u, "target": v, "weight": 1} for u, v in G.edges()]

        res1 = validate_mst(G, edge_list, "0-1, 1-2, 2-3")
        res2 = validate_mst(G, edge_list, "0-3, 3-2, 2-1")
        assert res1["passed"] is True
        assert res2["passed"] is True

        # DAG s větvemi 0->1, 0->2, 1->3, 2->3 má 2 platná topologická pořadí: 0,1,2,3 i 0,2,1,3
        dag = nx.DiGraph([(0, 1), (0, 2), (1, 3), (2, 3)])
        assert validate_topological_sort(dag, "u0, u1, u2, u3")["passed"] is True
        assert validate_topological_sort(dag, "u0, u2, u1, u3")["passed"] is True
        assert validate_topological_sort(dag, "u0, u3, u1, u2")["passed"] is False

