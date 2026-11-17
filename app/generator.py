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
    if getattr(config, 'force_bridge', False) and n >= 4 and not config.directed:
        G = _generate_with_bridge(n, m, rng, np_rng)
    elif config.bipartite:
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

        num_edges = G.number_of_edges()
        if getattr(config, 'unique_weights', False) and num_edges > 0:
            if (w_max - w_min + 1) < num_edges:
                w_max = w_min + num_edges - 1
            available_weights = list(range(w_min, w_max + 1))
            rng.shuffle(available_weights)
            for idx, (u, v) in enumerate(G.edges()):
                G[u][v]["weight"] = available_weights[idx]
        else:
            for u, v in G.edges():
                G[u][v]["weight"] = rng.randint(w_min, w_max)

        # Didaktická past: alespoň 1 záporná hrana pro Bellman-Ford bez záporného cyklu
        if getattr(config, 'allow_negative_edge', False) and G.is_directed() and num_edges > 1:
            edges = list(G.edges())
            # Upřednostni hrany, které neleží na orientovaném cyklu (zaručeně nevytvoří záporný cyklus)
            dag_like_edges = [
                (u, v) for (u, v) in edges
                if not nx.has_path(G, v, u)
            ]
            rng.shuffle(dag_like_edges)
            rng.shuffle(edges)
            candidates = dag_like_edges + [e for e in edges if e not in dag_like_edges]
            for u, v in candidates:
                orig_w = G[u][v].get("weight", 1)
                neg_w = -rng.randint(1, max(3, min(5, abs(orig_w))))
                G[u][v]["weight"] = neg_w
                if nx.negative_edge_cycle(G):
                    G[u][v]["weight"] = orig_w
                else:
                    break

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
        # Pro orientovaný graf: vytvoř orientovanou kostru (arborescenci) z uzlu 0,
        # aby byl každý uzel (zejména cílový n-1) dosažitelný ze startu 0.
        G = nx.DiGraph()
        G.add_nodes_from(range(n))
        if n >= 2:
            middle = list(range(1, n - 1))
            rng.shuffle(middle)
            order = [0] + middle + [n - 1]
            # Kostra směrem od 0 ke všem ostatním uzlům
            for i in range(1, n):
                parent_idx = rng.randint(0, i - 1)
                G.add_edge(order[parent_idx], order[i])

            # Zaruč, že i cílový uzel n-1 má alespoň jednoho předchůdce z vnitřních uzlů
            remaining_target = m - G.number_of_edges()
            if remaining_target > 0:
                # Upřednostni dopředné hrany v topologickém pořadí, aby vzniklo více cest 0 -> n-1
                forward_possible = []
                back_possible = []
                for idx_u, u in enumerate(order):
                    for idx_v, v in enumerate(order):
                        if u != v and not G.has_edge(u, v):
                            if idx_u < idx_v:
                                forward_possible.append((u, v))
                            else:
                                back_possible.append((u, v))
                rng.shuffle(forward_possible)
                rng.shuffle(back_possible)
                combined = forward_possible + back_possible
                G.add_edges_from(combined[:remaining_target])
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


def _generate_with_bridge(n: int, m: int, rng: random.Random,
                          np_rng: np.random.RandomState) -> nx.Graph:
    """
    Generuje souvislý neorientovaný graf se zaručeným mostem a artikulacemi.
    Rozdělí uzly na dvě disjunktní skupiny a propojí je jedinou hranou.
    """
    n_a = n // 2
    n_b = n - n_a
    nodes_a = list(range(n_a))
    nodes_b = list(range(n_a, n))

    G = nx.Graph()
    G.add_nodes_from(range(n))

    # Spanning tree v clusteru A
    rng.shuffle(nodes_a)
    for i in range(1, n_a):
        parent = rng.randint(0, i - 1)
        G.add_edge(nodes_a[i], nodes_a[parent])

    # Spanning tree v clusteru B
    rng.shuffle(nodes_b)
    for i in range(1, n_b):
        parent = rng.randint(0, i - 1)
        G.add_edge(nodes_b[i], nodes_b[parent])

    # Jediný most mezi clustery
    bridge_u = nodes_a[0]
    bridge_v = nodes_b[0]
    G.add_edge(bridge_u, bridge_v)

    # Zbylé hrany přidáváme pouze uvnitř clusterů A a B
    remaining = m - G.number_of_edges()
    if remaining > 0:
        internal_edges = []
        for i in range(n_a):
            for j in range(i + 1, n_a):
                if not G.has_edge(nodes_a[i], nodes_a[j]):
                    internal_edges.append((nodes_a[i], nodes_a[j]))
        for i in range(n_b):
            for j in range(i + 1, n_b):
                if not G.has_edge(nodes_b[i], nodes_b[j]):
                    internal_edges.append((nodes_b[i], nodes_b[j]))
        rng.shuffle(internal_edges)
        G.add_edges_from(internal_edges[:remaining])

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
