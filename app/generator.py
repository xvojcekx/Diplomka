"""
generator.py — Generátor grafů pomocí NetworkX

Generuje grafy podle zadaných parametrů (GraphConfig).
Podporuje: orientované/neorientované, ohodnocené, souvislé, acyklické (DAG/strom), bipartitní.
"""

import random
import networkx as nx
import numpy as np
from typing import Optional
from models import GraphConfig


def generate_graph(config: GraphConfig) -> dict:
    """
    Vygeneruje graf podle konfigurace.

    Returns:
        dict s klíči:
        - "graph": NetworkX graf
        - "adjacency_matrix": matice sousednosti (list of lists)
        - "edge_list": seznam hran [{"source", "target", "weight"?}]
        - "seed": použitý seed
    """
    seed = config.seed if config.seed is not None else random.randint(0, 999999)
    rng = random.Random(seed)
    np_rng = np.random.RandomState(seed)

    n = config.node_count
    m = config.edge_count

    # Validace parametrů
    _validate_config(config)

    # Generování grafu podle typu
    if config.bipartite:
        G = _generate_bipartite(n, m, config.directed, rng, np_rng)
    elif config.acyclic and config.directed:
        G = _generate_dag(n, m, config.connected, rng, np_rng)
    elif config.acyclic and not config.directed:
        G = _generate_tree(n, rng, np_rng)
    elif config.connected:
        G = _generate_connected(n, m, config.directed, rng, np_rng)
    else:
        G = _generate_random(n, m, config.directed, rng, np_rng)

    # Přidej váhy pokud ohodnocený
    if config.weighted:
        w_min = getattr(config, 'weight_min', 1)
        w_max = getattr(config, 'weight_max', 10)
        if w_min > w_max:
            w_min, w_max = w_max, w_min
            
        for u, v in G.edges():
            G[u][v]["weight"] = rng.randint(w_min, w_max)

    # Sestav výstup
    adjacency_matrix = _get_adjacency_matrix(G, config.weighted)
    edge_list = _get_edge_list(G, config.weighted)

    return {
        "graph": G,
        "adjacency_matrix": adjacency_matrix,
        "edge_list": edge_list,
        "seed": seed,
    }


def _validate_config(config: GraphConfig):
    """Zkontroluje realizovatelnost kombinace parametrů."""
    n = config.node_count
    m = config.edge_count

    if config.acyclic and not config.directed:
        # Strom: přesně n-1 hran
        if m != n - 1:
            raise ValueError(
                f"Acyklický neorientovaný graf (strom) musí mít přesně {n - 1} hran, "
                f"ale zadáno {m}."
            )

    if config.connected and not config.directed:
        if m < n - 1:
            raise ValueError(
                f"Souvislý graf s {n} uzly potřebuje minimálně {n - 1} hran, "
                f"ale zadáno {m}."
            )

    max_edges = n * (n - 1) if config.directed else n * (n - 1) // 2
    if config.acyclic and config.directed:
        max_edges = n * (n - 1) // 2  # DAG max

    if m > max_edges:
        raise ValueError(
            f"Pro {n} uzlů je maximální počet hran {max_edges}, ale zadáno {m}."
        )

    if config.bipartite:
        half_a = n // 2
        half_b = n - half_a
        max_bipartite = half_a * half_b
        if not config.directed:
            if m > max_bipartite:
                raise ValueError(
                    f"Bipartitní graf s {n} uzly ({half_a}+{half_b}) "
                    f"má max {max_bipartite} hran, ale zadáno {m}."
                )


def _generate_random(n: int, m: int, directed: bool, rng: random.Random,
                     np_rng: np.random.RandomState) -> nx.Graph:
    """Generuje náhodný graf (bez záruk)."""
    if directed:
        G = nx.DiGraph()
    else:
        G = nx.Graph()

    G.add_nodes_from(range(n))

    all_edges = []
    for i in range(n):
        for j in range(n):
            if i != j:
                if not directed and j <= i:
                    continue
                all_edges.append((i, j))

    rng.shuffle(all_edges)
    G.add_edges_from(all_edges[:m])
    return G


def _generate_connected(n: int, m: int, directed: bool, rng: random.Random,
                        np_rng: np.random.RandomState) -> nx.Graph:
    """Generuje souvislý graf — začne spanning tree, přidá zbylé hrany."""
    if directed:
        # Pro orientovaný: vytvoř neorientovaný connected, pak orientuj
        G_undir = _generate_connected(n, m, False, rng, np_rng)
        G = nx.DiGraph()
        G.add_nodes_from(range(n))
        for u, v in G_undir.edges():
            if rng.random() < 0.5:
                G.add_edge(u, v)
            else:
                G.add_edge(v, u)
        return G

    # Spanning tree jako základ
    G = nx.Graph()
    G.add_nodes_from(range(n))
    nodes = list(range(n))
    rng.shuffle(nodes)

    for i in range(1, n):
        parent = rng.randint(0, i - 1)
        G.add_edge(nodes[i], nodes[parent])

    # Přidej zbylé hrany
    remaining_target = m - (n - 1)
    if remaining_target > 0:
        possible = []
        for i in range(n):
            for j in range(i + 1, n):
                if not G.has_edge(i, j):
                    possible.append((i, j))
        rng.shuffle(possible)
        G.add_edges_from(possible[:remaining_target])

    return G


def _generate_dag(n: int, m: int, connected: bool, rng: random.Random,
                  np_rng: np.random.RandomState) -> nx.DiGraph:
    """Generuje DAG (orientovaný acyklický graf)."""
    G = nx.DiGraph()
    nodes = list(range(n))
    G.add_nodes_from(nodes)

    # Topologické pořadí = pořadí indexů (0 → 1 → 2 → ...)
    order = list(range(n))
    rng.shuffle(order)

    # Pokud má být connected, přidej cestu přes všechny uzly
    if connected:
        for i in range(n - 1):
            G.add_edge(order[i], order[i + 1])

    # Přidej zbylé hrany (vždy z nižšího do vyššího v order)
    remaining = m - G.number_of_edges()
    if remaining > 0:
        possible = []
        order_pos = {node: idx for idx, node in enumerate(order)}
        for i in range(n):
            for j in range(n):
                if i != j and order_pos[i] < order_pos[j] and not G.has_edge(i, j):
                    possible.append((i, j))
        rng.shuffle(possible)
        G.add_edges_from(possible[:remaining])

    return G


def _generate_tree(n: int, rng: random.Random,
                   np_rng: np.random.RandomState) -> nx.Graph:
    """Generuje náhodný strom (acyklický neorientovaný souvislý graf)."""
    G = nx.Graph()
    nodes = list(range(n))
    G.add_nodes_from(nodes)
    rng.shuffle(nodes)

    for i in range(1, n):
        parent = rng.randint(0, i - 1)
        G.add_edge(nodes[i], nodes[parent])

    return G


def _generate_bipartite(n: int, m: int, directed: bool, rng: random.Random,
                        np_rng: np.random.RandomState) -> nx.Graph:
    """Generuje bipartitní graf."""
    n_a = n // 2
    n_b = n - n_a

    set_a = list(range(n_a))
    set_b = list(range(n_a, n))

    if directed:
        G = nx.DiGraph()
    else:
        G = nx.Graph()

    G.add_nodes_from(range(n))

    # Označ uzly bipartitní skupinou
    for node in set_a:
        G.nodes[node]["bipartite"] = 0
    for node in set_b:
        G.nodes[node]["bipartite"] = 1

    # Všechny možné hrany mezi skupinami
    possible = []
    for a in set_a:
        for b in set_b:
            possible.append((a, b))
            if directed:
                possible.append((b, a))

    rng.shuffle(possible)
    G.add_edges_from(possible[:m])

    return G


def _get_adjacency_matrix(G: nx.Graph, weighted: bool) -> list:
    """Vrátí matici sousednosti jako list of lists."""
    nodes = sorted(G.nodes())
    n = len(nodes)
    node_idx = {node: i for i, node in enumerate(nodes)}

    matrix = [[0.0] * n for _ in range(n)]

    for u, v, data in G.edges(data=True):
        i, j = node_idx[u], node_idx[v]
        w = data.get("weight", 1) if weighted else 1
        matrix[i][j] = w
        if not G.is_directed():
            matrix[j][i] = w

    return matrix


def _get_edge_list(G: nx.Graph, weighted: bool) -> list:
    """Vrátí seznam hran jako list of dicts."""
    edges = []
    for u, v, data in G.edges(data=True):
        edge = {"source": int(u), "target": int(v)}
        if weighted:
            edge["weight"] = data.get("weight", 1)
        edges.append(edge)
    return edges
