"""
test_independent_verification.py — Nezávislé ověření správnosti výpočtů

Referenční hodnoty zde NEPOCHÁZEJÍ z knihovny NetworkX, na kterou se solver spoléhá.
Počítají se:
  - úplným prohledáním (hrubou silou) na malých grafech (nejkratší cesty, minimální kostra),
  - vlastní jednoduchou implementací Edmondsova–Karpova algoritmu (maximální tok),
  - ověřením vlastností výsledku podle definice úlohy (topologické uspořádání, mezizastávka bez opakování hran).

Dále ověřují garance generátoru a to, že validátor uzná všechna správná řešení.
Počty zkoušených grafů jsou uvedeny v konstantách N_* níže a citují se v textu práce.
"""

import itertools
import random
from collections import deque

import networkx as nx
import pytest

from generator import generate_graph
from grader import validate_mst, validate_topological_sort
from models import GraphConfig
from scenarios import build_scenario_for_graph, _find_edge_disjoint_stopover_path
from solver import (
    shortest_path_dijkstra,
    bellman_ford,
    minimum_spanning_tree,
    ford_fulkerson_max_flow,
    topological_sort,
    components_and_bridges,
)

N_DIJKSTRA = 200
N_BELLMAN = 150
N_MST = 150
N_FLOW = 150
N_TOPO = 100
N_GENERATOR = 100
N_SCENARIOS = 20
N_GRADER = 60

INF = float("inf")


# ----------------------------------------------------------------------------
# Pomocné nezávislé implementace
# ----------------------------------------------------------------------------

def brute_force_shortest(G, s, t):
    """Nejkratší cesta úplným průchodem všech jednoduchých cest (vhodné pro n ≤ 8)."""
    best = INF
    stack = [(s, {s}, 0)]
    while stack:
        u, seen, dist = stack.pop()
        if u == t:
            best = min(best, dist)
            continue
        for v in G.neighbors(u):
            if v not in seen:
                w = G[u][v].get("weight", 1)
                stack.append((v, seen | {v}, dist + w))
    return best


def brute_force_msts(G):
    """Vrátí (minimální váha, seznam všech minimálních koster jako množin hran)."""
    n = G.number_of_nodes()
    edges = [(u, v, d.get("weight", 1)) for u, v, d in G.edges(data=True)]
    best, winners = INF, []
    for combo in itertools.combinations(edges, n - 1):
        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        ok = True
        for u, v, _ in combo:
            ru, rv = find(u), find(v)
            if ru == rv:
                ok = False
                break
            parent[ru] = rv
        if not ok:
            continue
        total = sum(w for _, _, w in combo)
        if total < best:
            best, winners = total, [combo]
        elif total == best:
            winners.append(combo)
    return best, winners


def edmonds_karp(G, s, t):
    """Vlastní implementace maximálního toku (nezávislá na NetworkX)."""
    cap = {}
    adj = {u: set() for u in G.nodes()}
    for u, v, d in G.edges(data=True):
        cap[(u, v)] = cap.get((u, v), 0) + d.get("weight", 1)
        cap.setdefault((v, u), 0)
        adj[u].add(v)
        adj[v].add(u)
    flow = 0
    while True:
        parent = {s: None}
        queue = deque([s])
        while queue and t not in parent:
            u = queue.popleft()
            for v in adj[u]:
                if v not in parent and cap[(u, v)] > 0:
                    parent[v] = u
                    queue.append(v)
        if t not in parent:
            return flow
        delta, v = INF, t
        while parent[v] is not None:
            delta = min(delta, cap[(parent[v], v)])
            v = parent[v]
        v = t
        while parent[v] is not None:
            cap[(parent[v], v)] -= delta
            cap[(v, parent[v])] += delta
            v = parent[v]
        flow += delta


def make_graph(seed, directed, n_range=(4, 7), extra=(0, 5), **kw):
    rng = random.Random(seed)
    n = rng.randint(*n_range)
    max_m = n * (n - 1) if directed else n * (n - 1) // 2
    if kw.get("acyclic") and directed:
        max_m = n * (n - 1) // 2
    if kw.get("bipartite"):
        max_m = min(max_m, (n // 2) * (n - n // 2))
    m = min(max_m, n - 1 + rng.randint(*extra))
    cfg = GraphConfig(node_count=n, edge_count=m, directed=directed, seed=seed, **kw)
    return cfg, generate_graph(cfg)["graph"]


# ----------------------------------------------------------------------------
# Správnost algoritmů vůči nezávislé reference
# ----------------------------------------------------------------------------

def test_dijkstra_matches_bruteforce():
    for seed in range(N_DIJKSTRA):
        directed = seed % 2 == 0
        _, G = make_graph(seed, directed, weight_min=1, weight_max=9, connected=True)
        n = G.number_of_nodes()
        expected = brute_force_shortest(G, 0, n - 1)
        got = shortest_path_dijkstra(G, 0, n - 1)["distance"]
        assert got == expected, f"seed {seed}: {got} != {expected}"


def test_bellman_ford_matches_bruteforce_with_negative_edge():
    negatives = 0
    for seed in range(N_BELLMAN):
        _, G = make_graph(seed, True, weight_min=1, weight_max=9, connected=True,
                          allow_negative_edge=True)
        negatives += any(d["weight"] < 0 for _, _, d in G.edges(data=True))
        assert not nx.negative_edge_cycle(G)
        n = G.number_of_nodes()
        expected = brute_force_shortest(G, 0, n - 1)
        got = bellman_ford(G, 0, n - 1)["distance"]
        assert got == expected, f"seed {seed}: {got} != {expected}"
    assert negatives == N_BELLMAN, "každý graf měl obsahovat zápornou hranu"


def test_mst_weight_matches_bruteforce_and_unique_weights_give_unique_mst():
    for seed in range(N_MST):
        unique = seed % 2 == 0
        _, G = make_graph(seed, False, n_range=(4, 6), extra=(0, 4), weight_min=1,
                          weight_max=12, connected=True, unique_weights=unique)
        best, winners = brute_force_msts(G)
        assert minimum_spanning_tree(G)["total_weight"] == best, f"seed {seed}"
        if unique:
            assert len(winners) == 1, f"seed {seed}: kostra nebyla jednoznačná"


def test_max_flow_matches_independent_edmonds_karp():
    for seed in range(N_FLOW):
        _, G = make_graph(seed, True, weight_min=1, weight_max=15, connected=True)
        n = G.number_of_nodes()
        expected = edmonds_karp(G, 0, n - 1)
        got = ford_fulkerson_max_flow(G, 0, n - 1)
        assert got["max_flow"] == expected, f"seed {seed}"
        # věta o maximálním toku a minimálním řezu: kapacita řezu = tok
        cut = sum(e["capacity"] for e in got["min_cut_edges"])
        assert cut == expected, f"seed {seed}: řez {cut} != tok {expected}"


def test_topological_sort_is_valid_and_validator_detects_violations():
    for seed in range(N_TOPO):
        cfg, G = make_graph(seed, True, weight_min=1, weight_max=5, connected=True,
                            acyclic=True)
        order = topological_sort(G)["order"]
        pos = {v: i for i, v in enumerate(order)}
        assert sorted(order) == sorted(G.nodes())
        assert all(pos[u] < pos[v] for u, v in G.edges())
        answer = ", ".join(f"u{v}" for v in order)
        assert validate_topological_sort(G, answer)["passed"]
        # porušení: otočení pořadí musí být odmítnuto, existuje-li alespoň jedna hrana
        reversed_answer = ", ".join(f"u{v}" for v in reversed(order))
        assert not validate_topological_sort(G, reversed_answer)["passed"]


# ----------------------------------------------------------------------------
# Garance generátoru
# ----------------------------------------------------------------------------

def test_generator_guarantees():
    for seed in range(N_GENERATOR):
        rng = random.Random(seed)
        n = rng.randint(5, 12)
        # souvislý orientovaný graf: cíl n-1 je dosažitelný ze startu 0
        _, G = make_graph(seed, True, n_range=(n, n), connected=True)
        assert nx.has_path(G, 0, n - 1), f"seed {seed}: cíl nedosažitelný"
        # orientovaný acyklický graf
        _, D = make_graph(seed, True, n_range=(n, n), acyclic=True)
        assert nx.is_directed_acyclic_graph(D)
        # bipartitní graf
        _, B = make_graph(seed, False, n_range=(n, n), bipartite=True, connected=False)
        assert nx.is_bipartite(B)
        # zaručený most
        _, M = make_graph(seed, False, n_range=(max(n, 6), max(n, 6)), connected=True,
                          force_bridge=True)
        assert nx.is_connected(M)
        assert len(list(nx.bridges(M))) >= 1, f"seed {seed}: žádný most"
        # reprodukovatelnost
        a = make_graph(seed, False, n_range=(n, n), connected=True)[1]
        b = make_graph(seed, False, n_range=(n, n), connected=True)[1]
        assert sorted(a.edges(data="weight")) == sorted(b.edges(data="weight"))


# ----------------------------------------------------------------------------
# Scénáře písemek
# ----------------------------------------------------------------------------

PRESETS = {
    "dijkstra": dict(node_count=7, edge_count=10, weight_min=2, weight_max=14),
    "dijkstra_stopover": dict(node_count=8, edge_count=12, weight_min=2, weight_max=15),
    "kruskal": dict(node_count=7, edge_count=11, weight_min=1, weight_max=16, unique_weights=True),
    "bellman_ford": dict(node_count=6, edge_count=9, directed=True, weight_min=1,
                         weight_max=12, allow_negative_edge=True),
    "bridges": dict(node_count=8, edge_count=10, weight_min=1, weight_max=10, force_bridge=True),
    "toposort": dict(node_count=7, edge_count=9, directed=True, weighted=False, acyclic=True),
    "max_flow": dict(node_count=6, edge_count=9, directed=True, weight_min=2, weight_max=15),
}


def graph_data_for(cfg):
    result = generate_graph(cfg)
    return {
        "config": cfg.model_dump(),
        "properties": {"node_count": cfg.node_count},
        "edge_list": result["edge_list"],
        "algorithms": {},
    }, result["graph"]


@pytest.mark.parametrize("preset", sorted(PRESETS))
def test_every_scenario_builds_complete_assignment_and_key(preset):
    for seed in range(N_SCENARIOS):
        cfg = GraphConfig(connected=True, seed=seed, **PRESETS[preset])
        data, _ = graph_data_for(cfg)
        sc = build_scenario_for_graph(data, scenario_type=preset)
        assert sc["scenario_type"] == preset
        assert sc["story"] and sc["questions"] and sc["student_table_html"]
        assert sc["teacher_solution"]
        for bad in ("None", "nan", "Traceback"):
            assert bad not in sc["teacher_solution"], f"{preset} seed {seed}: '{bad}'"


def test_stopover_route_never_repeats_an_edge():
    checked = 0
    for seed in range(N_SCENARIOS * 5):
        cfg = GraphConfig(connected=True, seed=seed, **PRESETS["dijkstra_stopover"])
        _, G = graph_data_for(cfg)
        sc_nodes = sorted(G.nodes())
        s, t = sc_nodes[0], sc_nodes[-1]
        for m in sc_nodes[1:-1]:
            res = _find_edge_disjoint_stopover_path(G, s, m, t)
            if not res["valid"] or not res["edge_disjoint"]:
                continue
            walk = res["full_path"]
            used = [frozenset(e) for e in zip(walk, walk[1:])]
            assert len(used) == len(set(used)), f"seed {seed}, M={m}: hrana opakována"
            # délka nesmí být menší než nejkratší cesta bez omezení S→M→T
            lower = brute_force_shortest(G, s, m) + brute_force_shortest(G, m, t)
            assert res["total_distance"] >= lower
            checked += 1
    assert checked > 0


# ----------------------------------------------------------------------------
# Validátor uzná všechna správná řešení
# ----------------------------------------------------------------------------

def test_mst_validator_accepts_every_minimal_tree_and_rejects_heavier_ones():
    accepted = 0
    for seed in range(N_GRADER):
        # malé váhy → časté shody → více minimálních koster
        cfg, G = make_graph(seed, False, n_range=(4, 6), extra=(1, 4), weight_min=1,
                            weight_max=3, connected=True)
        best, winners = brute_force_msts(G)
        edge_list = [{"source": u, "target": v, "weight": d.get("weight", 1)}
                     for u, v, d in G.edges(data=True)]
        for combo in winners:
            answer = ", ".join(f"u{u}-u{v}" for u, v, _ in combo)
            assert validate_mst(G, edge_list, answer)["passed"], f"seed {seed}: {answer}"
            accepted += 1
        # nejtěžší kostra, je-li těžší než optimum, musí být odmítnuta
        edges = [(u, v, d.get("weight", 1)) for u, v, d in G.edges(data=True)]
        worst = None
        for combo in itertools.combinations(edges, G.number_of_nodes() - 1):
            sub = nx.Graph([(u, v) for u, v, _ in combo])
            if sub.number_of_nodes() == G.number_of_nodes() and nx.is_connected(sub):
                w = sum(x for _, _, x in combo)
                if worst is None or w > worst[0]:
                    worst = (w, combo)
        if worst and worst[0] > best:
            answer = ", ".join(f"u{u}-u{v}" for u, v, _ in worst[1])
            assert not validate_mst(G, edge_list, answer)["passed"]
    assert accepted >= N_GRADER
