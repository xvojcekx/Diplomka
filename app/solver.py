"""
solver.py — Algoritmy na grafech

Implementuje klíčové grafové algoritmy pro výpočet výsledků zadání.
Každý algoritmus vrací strukturovaný dict s výsledky.
"""

import networkx as nx
from typing import Optional


# ============================================================================
# IMPLEMENTOVANÉ ALGORITMY
# ============================================================================

def shortest_path_dijkstra(G: nx.Graph, source: int, target: int) -> dict:
    """
    Dijkstrův algoritmus — nejkratší cesta.

    Args:
        G: NetworkX graf (ohodnocený)
        source: počáteční uzel
        target: cílový uzel

    Returns:
        dict: {"path": [...], "distance": float, "steps": [...popis kroků...], "error": str|None}
    """
    try:
        if not nx.has_path(G, source, target):
            return {
                "path": [],
                "distance": float("inf"),
                "steps": [],
                "error": f"Neexistuje cesta z uzlu {source} do uzlu {target}."
            }

        weight = "weight" if nx.is_weighted(G) else None
        path = nx.shortest_path(G, source=source, target=target, weight=weight)
        distance = nx.shortest_path_length(G, source=source, target=target, weight=weight)

        # Kroky cesty
        steps = []
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            w = G[u][v].get("weight", 1)
            steps.append(f"{u} → {v} (váha: {w})")

        return {
            "path": path,
            "distance": float(distance),
            "steps": steps,
            "error": None
        }
    except Exception as e:
        return {
            "path": [],
            "distance": float("inf"),
            "steps": [],
            "error": str(e)
        }


def minimum_spanning_tree(G: nx.Graph) -> dict:
    """
    Kruskalův algoritmus — minimální kostra.

    Args:
        G: NetworkX graf (neorientovaný, ohodnocený)

    Returns:
        dict: {"tree_edges": [...], "total_weight": float, "error": str|None}
    """
    try:
        if G.is_directed():
            return {
                "tree_edges": [],
                "total_weight": 0,
                "error": "MST je definován pouze pro neorientované grafy."
            }

        if not nx.is_connected(G):
            return {
                "tree_edges": [],
                "total_weight": 0,
                "error": "Graf není souvislý — MST nelze spočítat."
            }

        mst = nx.minimum_spanning_tree(G, algorithm="kruskal")
        tree_edges = []
        total_weight = 0

        for u, v, data in sorted(mst.edges(data=True), key=lambda x: x[2].get("weight", 1)):
            w = data.get("weight", 1)
            tree_edges.append({"source": int(u), "target": int(v), "weight": w})
            total_weight += w

        return {
            "tree_edges": tree_edges,
            "total_weight": float(total_weight),
            "error": None
        }
    except Exception as e:
        return {
            "tree_edges": [],
            "total_weight": 0,
            "error": str(e)
        }


def topological_sort(G: nx.Graph) -> dict:
    """
    Topologické třídění (jen pro DAG).

    Args:
        G: NetworkX orientovaný graf

    Returns:
        dict: {"order": [...], "valid": bool, "error": str|None}
    """
    try:
        if not G.is_directed():
            return {
                "order": [],
                "valid": False,
                "error": "Topologické třídění je definováno pouze pro orientované grafy."
            }

        if not nx.is_directed_acyclic_graph(G):
            return {
                "order": [],
                "valid": False,
                "error": "Graf obsahuje cyklus — topologické třídění neexistuje."
            }

        order = list(nx.topological_sort(G))
        return {
            "order": order,
            "valid": True,
            "error": None
        }
    except Exception as e:
        return {
            "order": [],
            "valid": False,
            "error": str(e)
        }


def is_bipartite_check(G: nx.Graph) -> dict:
    """
    Ověření bipartitnosti + rozdělení do skupin.

    Args:
        G: NetworkX graf

    Returns:
        dict: {"is_bipartite": bool, "sets": (list, list)|None, "error": str|None}
    """
    try:
        is_bip = nx.is_bipartite(G)
        sets = None

        if is_bip:
            set_a, set_b = nx.bipartite.sets(G)
            sets = (sorted(list(set_a)), sorted(list(set_b)))

        return {
            "is_bipartite": is_bip,
            "sets": sets,
            "error": None
        }
    except Exception as e:
        return {
            "is_bipartite": False,
            "sets": None,
            "error": str(e)
        }


def graph_properties(G: nx.Graph) -> dict:
    """
    Základní vlastnosti grafu.

    Returns:
        dict s klíči: node_count, edge_count, is_connected, is_directed,
        is_weighted, density, diameter, degree_sequence
    """
    try:
        props = {
            "node_count": G.number_of_nodes(),
            "edge_count": G.number_of_edges(),
            "is_directed": G.is_directed(),
            "is_weighted": nx.is_weighted(G),
            "density": round(nx.density(G), 4),
        }

        # Souvislost
        if G.is_directed():
            props["is_connected"] = nx.is_weakly_connected(G)
        else:
            props["is_connected"] = nx.is_connected(G)

        # Průměr (jen pokud je souvislý)
        if props["is_connected"]:
            if G.is_directed():
                try:
                    props["diameter"] = nx.diameter(G.to_undirected())
                except Exception:
                    props["diameter"] = "N/A"
            else:
                props["diameter"] = nx.diameter(G)
        else:
            props["diameter"] = "N/A (nesouvislý)"

        # Zaměřeno na konkrétní extrémy
        degrees = dict(G.degree())
        if degrees:
            max_deg = max(degrees.values())
            min_deg = min(degrees.values())
            props["max_degree_val"] = max_deg
            props["max_degree_nodes"] = [f"u{k}" for k, v in degrees.items() if v == max_deg]
            props["min_degree_val"] = min_deg
            props["min_degree_nodes"] = [f"u{k}" for k, v in degrees.items() if v == min_deg]
            
        if nx.is_weighted(G) and G.number_of_edges() > 0:
            weights = {(u, v): d.get("weight", 0) for u, v, d in G.edges(data=True)}
            if weights:
                max_w = max(weights.values())
                min_w = min(weights.values())
                props["max_weight_val"] = max_w
                # formátování s 'u' pouze pro zobrazení
                props["max_weight_edges"] = [f"u{u}-u{v}" for (u, v), w in weights.items() if w == max_w]
                props["min_weight_val"] = min_w
                props["min_weight_edges"] = [f"u{u}-u{v}" for (u, v), w in weights.items() if w == min_w]

        # Stupňová sekvence (pro expertní analýzu / dokumentaci)
        props["degree_sequence"] = sorted([d for _, d in G.degree()], reverse=True)

        return props
    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# KROKOVÉ ALGORITMY PRO VIZUALIZACI
# ============================================================================

def kruskal_steps(G: nx.Graph) -> dict:
    """
    Kruskalův algoritmus — krok po kroku pro vizualizaci.
    Seřadí hrany dle váhy, iteruje, Union-Find kontrola.

    Returns:
        dict s klíči: algorithm, steps, result_edges, total_weight, error
    """
    try:
        if G.is_directed():
            return {"error": "Kruskal je definován pouze pro neorientované grafy."}
        if not nx.is_connected(G):
            return {"error": "Graf není souvislý — MST nelze spočítat."}

        # Seřazené hrany dle váhy
        edges_sorted = sorted(G.edges(data=True), key=lambda x: x[2].get("weight", 1))

        # Union-Find
        parent = {n: n for n in G.nodes()}
        rank = {n: 0 for n in G.nodes()}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x, y):
            rx, ry = find(x), find(y)
            if rx == ry:
                return False
            if rank[rx] < rank[ry]:
                rx, ry = ry, rx
            parent[ry] = rx
            if rank[rx] == rank[ry]:
                rank[rx] += 1
            return True

        steps = []
        selected_edges = []
        total_weight = 0
        step_num = 0

        # Krok 0: inicializace
        steps.append({
            "step": step_num,
            "action": "init",
            "edge": None,
            "weight": None,
            "description": f"Inicializace: {G.number_of_nodes()} uzlů, {G.number_of_edges()} hran. "
                          f"Hrany seřazeny dle váhy vzestupně.",
            "selected_edges": [],
            "current_edge": None,
            "highlight_nodes": [],
        })
        step_num += 1

        for u, v, data in edges_sorted:
            w = data.get("weight", 1)
            edge = [int(u), int(v)]

            # Krok: zkoumáme hranu
            steps.append({
                "step": step_num,
                "action": "examine",
                "edge": edge,
                "weight": w,
                "description": f"Zkoumáme hranu {u}–{v} (váha {w}).",
                "selected_edges": [list(e) for e in selected_edges],
                "current_edge": edge,
                "highlight_nodes": [int(u), int(v)],
            })
            step_num += 1

            if union(u, v):
                # Přijata
                selected_edges.append(edge)
                total_weight += w
                steps.append({
                    "step": step_num,
                    "action": "accept",
                    "edge": edge,
                    "weight": w,
                    "description": f"Hrana {u}–{v} (váha {w}) PŘIJATA — uzly jsou v různých komponentách.",
                    "selected_edges": [list(e) for e in selected_edges],
                    "current_edge": edge,
                    "highlight_nodes": [int(u), int(v)],
                })
            else:
                # Zamítnuta
                steps.append({
                    "step": step_num,
                    "action": "reject",
                    "edge": edge,
                    "weight": w,
                    "description": f"Hrana {u}–{v} (váha {w}) ZAMÍTNUTA — uzly jsou ve stejné komponentě (vznikl by cyklus).",
                    "selected_edges": [list(e) for e in selected_edges],
                    "current_edge": edge,
                    "highlight_nodes": [int(u), int(v)],
                })
            step_num += 1

        # Finální krok
        steps.append({
            "step": step_num,
            "action": "done",
            "edge": None,
            "weight": None,
            "description": f"Hotovo! Minimální kostra má {len(selected_edges)} hran s celkovou váhou {total_weight}.",
            "selected_edges": [list(e) for e in selected_edges],
            "current_edge": None,
            "highlight_nodes": [],
        })

        return {
            "algorithm": "kruskal",
            "algorithm_name": "Kruskalův algoritmus",
            "steps": steps,
            "result_edges": [list(e) for e in selected_edges],
            "total_weight": float(total_weight),
            "error": None,
        }
    except Exception as e:
        return {"error": str(e)}


def boruvka_steps(G: nx.Graph) -> dict:
    """
    Borůvkův algoritmus — krok po kroku pro vizualizaci.
    Iterace komponent, nejlevnější hrana každé komponenty.

    Returns:
        dict s klíči: algorithm, steps, result_edges, total_weight, error
    """
    try:
        if G.is_directed():
            return {"error": "Borůvka je definován pouze pro neorientované grafy."}
        if not nx.is_connected(G):
            return {"error": "Graf není souvislý — MST nelze spočítat."}

        # Inicializace: každý uzel = vlastní komponenta
        component = {n: n for n in G.nodes()}
        num_components = G.number_of_nodes()

        def find_comp(x):
            while component[x] != x:
                component[x] = component[component[x]]
                x = component[x]
            return x

        def merge_comp(x, y):
            rx, ry = find_comp(x), find_comp(y)
            if rx != ry:
                component[ry] = rx
                return True
            return False

        steps = []
        selected_edges = []
        total_weight = 0
        step_num = 0
        iteration = 0

        steps.append({
            "step": step_num,
            "action": "init",
            "edge": None,
            "weight": None,
            "description": f"Inicializace: {G.number_of_nodes()} komponent (každý uzel = vlastní komponenta).",
            "selected_edges": [],
            "current_edge": None,
            "highlight_nodes": [],
        })
        step_num += 1

        while num_components > 1:
            iteration += 1
            # Najdi nejlevnější hranu pro každou komponentu
            cheapest = {}

            for u, v, data in G.edges(data=True):
                w = data.get("weight", 1)
                cu, cv = find_comp(u), find_comp(v)
                if cu == cv:
                    continue
                if cu not in cheapest or cheapest[cu][2] > w:
                    cheapest[cu] = (u, v, w)
                if cv not in cheapest or cheapest[cv][2] > w:
                    cheapest[cv] = (u, v, w)

            if not cheapest:
                break

            steps.append({
                "step": step_num,
                "action": "examine",
                "edge": None,
                "weight": None,
                "description": f"Iterace {iteration}: hledáme nejlevnější hranu pro každou komponentu ({num_components} komponent).",
                "selected_edges": [list(e) for e in selected_edges],
                "current_edge": None,
                "highlight_nodes": [],
            })
            step_num += 1

            added_in_round = set()
            for comp_id, (u, v, w) in cheapest.items():
                edge_key = tuple(sorted([int(u), int(v)]))
                if edge_key in added_in_round:
                    continue

                if merge_comp(u, v):
                    added_in_round.add(edge_key)
                    edge = [int(u), int(v)]
                    selected_edges.append(edge)
                    total_weight += w
                    num_components -= 1

                    steps.append({
                        "step": step_num,
                        "action": "accept",
                        "edge": edge,
                        "weight": w,
                        "description": f"Iterace {iteration}: hrana {u}–{v} (váha {w}) PŘIJATA — nejlevnější hrana komponenty.",
                        "selected_edges": [list(e) for e in selected_edges],
                        "current_edge": edge,
                        "highlight_nodes": [int(u), int(v)],
                    })
                    step_num += 1

        steps.append({
            "step": step_num,
            "action": "done",
            "edge": None,
            "weight": None,
            "description": f"Hotovo! Minimální kostra má {len(selected_edges)} hran s celkovou váhou {total_weight}.",
            "selected_edges": [list(e) for e in selected_edges],
            "current_edge": None,
            "highlight_nodes": [],
        })

        return {
            "algorithm": "boruvka",
            "algorithm_name": "Borůvkův algoritmus",
            "steps": steps,
            "result_edges": [list(e) for e in selected_edges],
            "total_weight": float(total_weight),
            "error": None,
        }
    except Exception as e:
        return {"error": str(e)}


def dijkstra_steps(G: nx.Graph, source: int, target: int) -> dict:
    """
    Dijkstrův algoritmus — krok po kroku pro vizualizaci.
    Priority queue, relakace hran, finální cesta.

    Returns:
        dict s klíči: algorithm, steps, result_edges, total_weight, error
    """
    import heapq

    try:
        if not nx.has_path(G, source, target):
            return {"error": f"Neexistuje cesta z uzlu {source} do uzlu {target}."}

        dist = {n: float("inf") for n in G.nodes()}
        prev = {n: None for n in G.nodes()}
        dist[source] = 0
        visited = set()
        pq = [(0, int(source))]

        steps = []
        step_num = 0

        steps.append({
            "step": step_num,
            "action": "init",
            "edge": None,
            "weight": None,
            "description": f"Inicializace: zdroj = {source}, cíl = {target}. "
                          f"Vzdálenost zdroje = 0, ostatní = ∞.",
            "selected_edges": [],
            "current_edge": None,
            "highlight_nodes": [int(source)],
            "distances": {str(n): (dist[n] if dist[n] != float("inf") else "∞") for n in G.nodes()},
        })
        step_num += 1

        path_edges = []

        while pq:
            d, u = heapq.heappop(pq)
            if u in visited:
                continue
            visited.add(u)

            # Uzel navštíven
            steps.append({
                "step": step_num,
                "action": "examine",
                "edge": [int(prev[u]), int(u)] if prev[u] is not None else None,
                "weight": d,
                "description": f"Navštěvujeme uzel {u} (vzdálenost {d}). "
                              f"Prozkoumáme jeho sousedy.",
                "selected_edges": [list(e) for e in path_edges],
                "current_edge": [int(prev[u]), int(u)] if prev[u] is not None else None,
                "highlight_nodes": [int(u)],
                "distances": {str(n): (dist[n] if dist[n] != float("inf") else "∞") for n in G.nodes()},
            })
            step_num += 1

            if u == target:
                break

            neighbors = G.neighbors(u)
            for v in neighbors:
                if v in visited:
                    continue
                w = G[u][v].get("weight", 1)
                new_dist = d + w
                edge = [int(u), int(v)]

                if new_dist < dist[v]:
                    dist[v] = new_dist
                    prev[v] = u
                    heapq.heappush(pq, (new_dist, int(v)))

                    steps.append({
                        "step": step_num,
                        "action": "accept",
                        "edge": edge,
                        "weight": w,
                        "description": f"Relakace hrany {u}→{v} (váha {w}): {d} + {w} = {new_dist} < {dist[v] if dist[v] != new_dist else '∞'} → aktualizujeme.",
                        "selected_edges": [list(e) for e in path_edges],
                        "current_edge": edge,
                        "highlight_nodes": [int(u), int(v)],
                        "distances": {str(n): (dist[n] if dist[n] != float("inf") else "∞") for n in G.nodes()},
                    })
                    step_num += 1
                else:
                    steps.append({
                        "step": step_num,
                        "action": "reject",
                        "edge": edge,
                        "weight": w,
                        "description": f"Hrana {u}→{v} (váha {w}): {d} + {w} = {new_dist} ≥ {dist[v]} → neaktualizujeme.",
                        "selected_edges": [list(e) for e in path_edges],
                        "current_edge": edge,
                        "highlight_nodes": [int(u), int(v)],
                        "distances": {str(n): (dist[n] if dist[n] != float("inf") else "∞") for n in G.nodes()},
                    })
                    step_num += 1

        # Rekonstrukce cesty
        path = []
        node = target
        while node is not None:
            path.append(int(node))
            node = prev[node]
        path.reverse()

        if len(path) > 1:
            path_edges = [[path[i], path[i + 1]] for i in range(len(path) - 1)]

        steps.append({
            "step": step_num,
            "action": "done",
            "edge": None,
            "weight": None,
            "description": f"Hotovo! Nejkratší cesta: {' → '.join(map(str, path))} s délkou {dist[target]}.",
            "selected_edges": path_edges,
            "current_edge": None,
            "highlight_nodes": path,
            "distances": {str(n): (dist[n] if dist[n] != float("inf") else "∞") for n in G.nodes()},
        })

        return {
            "algorithm": "dijkstra",
            "algorithm_name": "Dijkstrův algoritmus",
            "steps": steps,
            "result_edges": path_edges,
            "total_weight": float(dist[target]),
            "source": int(source),
            "target": int(target),
            "error": None,
        }
    except Exception as e:
        return {"error": str(e)}


def bfs_steps(G: nx.Graph, source: int) -> dict:
    """
    BFS průchod — krok po kroku pro vizualizaci.

    Returns:
        dict s klíči: algorithm, steps, result_edges, error
    """
    try:
        from collections import deque

        visited = set()
        queue = deque([int(source)])
        visited.add(int(source))

        steps = []
        tree_edges = []
        step_num = 0

        steps.append({
            "step": step_num,
            "action": "init",
            "edge": None,
            "weight": None,
            "description": f"Inicializace BFS: začínáme z uzlu {source}. Fronta: [{source}].",
            "selected_edges": [],
            "current_edge": None,
            "highlight_nodes": [int(source)],
        })
        step_num += 1

        while queue:
            u = queue.popleft()

            steps.append({
                "step": step_num,
                "action": "examine",
                "edge": None,
                "weight": None,
                "description": f"Vyjímáme uzel {u} z fronty. Prozkoumáme sousedy.",
                "selected_edges": [list(e) for e in tree_edges],
                "current_edge": None,
                "highlight_nodes": [int(u)],
            })
            step_num += 1

            for v in sorted(G.neighbors(u)):
                v = int(v)
                edge = [int(u), v]

                if v not in visited:
                    visited.add(v)
                    queue.append(v)
                    tree_edges.append(edge)

                    steps.append({
                        "step": step_num,
                        "action": "accept",
                        "edge": edge,
                        "weight": G[u][v].get("weight", None),
                        "description": f"Uzel {v} nenavštíven → přidáváme do fronty. Hrana {u}–{v} přidána do BFS stromu.",
                        "selected_edges": [list(e) for e in tree_edges],
                        "current_edge": edge,
                        "highlight_nodes": [int(u), v],
                    })
                    step_num += 1
                else:
                    steps.append({
                        "step": step_num,
                        "action": "reject",
                        "edge": edge,
                        "weight": G[u][v].get("weight", None),
                        "description": f"Uzel {v} už byl navštíven → přeskakujeme.",
                        "selected_edges": [list(e) for e in tree_edges],
                        "current_edge": edge,
                        "highlight_nodes": [int(u), v],
                    })
                    step_num += 1

        steps.append({
            "step": step_num,
            "action": "done",
            "edge": None,
            "weight": None,
            "description": f"BFS dokončen! Navštíveno {len(visited)} uzlů, BFS strom má {len(tree_edges)} hran.",
            "selected_edges": [list(e) for e in tree_edges],
            "current_edge": None,
            "highlight_nodes": list(visited),
        })

        return {
            "algorithm": "bfs",
            "algorithm_name": "BFS (prohledávání do šířky)",
            "steps": steps,
            "result_edges": [list(e) for e in tree_edges],
            "error": None,
        }
    except Exception as e:
        return {"error": str(e)}


def dfs_steps(G: nx.Graph, source: int) -> dict:
    """
    DFS průchod — krok po kroku pro vizualizaci.

    Returns:
        dict s klíči: algorithm, steps, result_edges, error
    """
    try:
        visited = set()
        stack = [int(source)]

        steps = []
        tree_edges = []
        step_num = 0
        came_from = {int(source): None}

        steps.append({
            "step": step_num,
            "action": "init",
            "edge": None,
            "weight": None,
            "description": f"Inicializace DFS: začínáme z uzlu {source}. Zásobník: [{source}].",
            "selected_edges": [],
            "current_edge": None,
            "highlight_nodes": [int(source)],
        })
        step_num += 1

        while stack:
            u = stack.pop()
            u = int(u)

            if u in visited:
                continue

            visited.add(u)
            parent = came_from.get(u)

            if parent is not None:
                edge = [int(parent), u]
                tree_edges.append(edge)
                steps.append({
                    "step": step_num,
                    "action": "accept",
                    "edge": edge,
                    "weight": G[parent][u].get("weight", None),
                    "description": f"Navštěvujeme uzel {u} (z uzlu {parent}). Hrana {parent}–{u} přidána do DFS stromu.",
                    "selected_edges": [list(e) for e in tree_edges],
                    "current_edge": edge,
                    "highlight_nodes": [int(parent), u],
                })
                step_num += 1
            else:
                steps.append({
                    "step": step_num,
                    "action": "examine",
                    "edge": None,
                    "weight": None,
                    "description": f"Navštěvujeme počáteční uzel {u}.",
                    "selected_edges": [list(e) for e in tree_edges],
                    "current_edge": None,
                    "highlight_nodes": [u],
                })
                step_num += 1

            for v in sorted(G.neighbors(u), reverse=True):
                v = int(v)
                edge = [u, v]
                if v not in visited:
                    stack.append(v)
                    came_from[v] = u
                else:
                    steps.append({
                        "step": step_num,
                        "action": "reject",
                        "edge": edge,
                        "weight": G[u][v].get("weight", None),
                        "description": f"Uzel {v} už byl navštíven → přeskakujeme hranu {u}–{v}.",
                        "selected_edges": [list(e) for e in tree_edges],
                        "current_edge": edge,
                        "highlight_nodes": [u, v],
                    })
                    step_num += 1

        steps.append({
            "step": step_num,
            "action": "done",
            "edge": None,
            "weight": None,
            "description": f"DFS dokončen! Navštíveno {len(visited)} uzlů, DFS strom má {len(tree_edges)} hran.",
            "selected_edges": [list(e) for e in tree_edges],
            "current_edge": None,
            "highlight_nodes": list(visited),
        })

        return {
            "algorithm": "dfs",
            "algorithm_name": "DFS (prohledávání do hloubky)",
            "steps": steps,
            "result_edges": [list(e) for e in tree_edges],
            "error": None,
        }
    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# POKROČILÉ ALGORITMY (SEKCE A)
# ============================================================================

def ford_fulkerson_max_flow(G: nx.Graph, source: int = None, sink: int = None) -> dict:
    """
    Edmonds-Karp / Ford-Fulkerson — maximální tok v síti a minimální řez.

    Args:
        G: Graf s kapacitami (weight) na hranách
        source: zdrojový uzel (výchozí: první uzel)
        sink: spotřebič / stoka (výchozí: poslední uzel)

    Returns:
        dict: {
            "max_flow": float,
            "source": int,
            "sink": int,
            "flow_edges": list[{"source", "target", "flow", "capacity"}],
            "min_cut_value": float,
            "min_cut_sets": (list, list),
            "min_cut_edges": list[{"source", "target", "capacity"}],
            "error": str|None
        }
    """
    try:
        if G.number_of_nodes() < 2:
            return {"max_flow": 0, "error": "Graf musí mít alespoň 2 uzly."}

        nodes = sorted(G.nodes())
        if source is None or source not in nodes:
            source = nodes[0]
        if sink is None or sink not in nodes:
            sink = nodes[-1]
        if source == sink:
            return {"max_flow": 0, "error": "Zdroj a spotřebič musí být různé uzly."}

        # Vytvoř pomocný graf s nezápornými kapacitami v atributu 'capacity'
        H = nx.DiGraph() if G.is_directed() else nx.Graph()
        H.add_nodes_from(G.nodes())
        for u, v, d in G.edges(data=True):
            w = d.get("weight", 1)
            if w < 0:
                return {
                    "max_flow": 0,
                    "error": "Maximální tok vyžaduje nezáporné kapacity hran."
                }
            H.add_edge(int(u), int(v), capacity=float(w))

        flow_val, flow_dict = nx.maximum_flow(H, int(source), int(sink), capacity="capacity")
        cut_val, (set_s, set_t) = nx.minimum_cut(H, int(source), int(sink), capacity="capacity")

        flow_edges = []
        for u, v, d in H.edges(data=True):
            cap = d["capacity"]
            f_uv = flow_dict.get(u, {}).get(v, 0)
            if not G.is_directed() and f_uv == 0:
                f_uv = flow_dict.get(v, {}).get(u, 0)
            if f_uv > 0 or cap > 0:
                flow_edges.append({
                    "source": int(u),
                    "target": int(v),
                    "flow": int(f_uv) if float(f_uv).is_integer() else round(float(f_uv), 2),
                    "capacity": int(cap) if float(cap).is_integer() else round(float(cap), 2),
                })

        min_cut_edges = []
        for u in set_s:
            for v in H.neighbors(u):
                if v in set_t:
                    cap = H[u][v]["capacity"]
                    min_cut_edges.append({
                        "source": int(u),
                        "target": int(v),
                        "capacity": int(cap) if float(cap).is_integer() else round(float(cap), 2),
                    })

        return {
            "max_flow": int(flow_val) if float(flow_val).is_integer() else round(float(flow_val), 2),
            "source": int(source),
            "sink": int(sink),
            "flow_edges": flow_edges,
            "min_cut_value": int(cut_val) if float(cut_val).is_integer() else round(float(cut_val), 2),
            "min_cut_sets": (sorted([int(x) for x in set_s]), sorted([int(x) for x in set_t])),
            "min_cut_edges": min_cut_edges,
            "error": None,
        }
    except Exception as e:
        return {"max_flow": 0, "error": str(e)}


def bellman_ford(G: nx.Graph, source: int = None, target: int = None) -> dict:
    """
    Bellman-Fordův algoritmus — nejkratší cesty i pro grafy se zápornými vahami hran.

    Args:
        G: NetworkX graf (může mít záporné váhy)
        source: počáteční uzel (výchozí: první uzel)
        target: volitelný cílový uzel (výchozí: poslední uzel)

    Returns:
        dict: {
            "source": int,
            "target": int,
            "path": list,
            "distance": float,
            "distances": dict,
            "negative_cycle": bool,
            "error": str|None
        }
    """
    try:
        if G.number_of_nodes() == 0:
            return {"negative_cycle": False, "error": "Graf je prázdný."}

        nodes = sorted(G.nodes())
        if source is None or source not in nodes:
            source = nodes[0]
        if target is None or target not in nodes:
            target = nodes[-1]

        weight = "weight" if nx.is_weighted(G) else None

        if nx.negative_edge_cycle(G, weight=weight or "weight"):
            return {
                "source": int(source),
                "target": int(target),
                "path": [],
                "distance": float("-inf"),
                "distances": {},
                "negative_cycle": True,
                "error": "Graf obsahuje záporný cyklus dosažitelný v síti — nejkratší cesta není konečná."
            }

        preds, dists = nx.bellman_ford_predecessor_and_distance(G, source=source, weight=weight)
        clean_dists = {
            f"u{int(k)}": (int(v) if isinstance(v, (int, float)) and float(v).is_integer() else round(float(v), 2))
            for k, v in sorted(dists.items())
        }

        if target not in dists:
            return {
                "source": int(source),
                "target": int(target),
                "path": [],
                "distance": float("inf"),
                "distances": clean_dists,
                "negative_cycle": False,
                "error": f"Cílový uzel u{target} není z uzlu u{source} dosažitelný."
            }

        path = nx.bellman_ford_path(G, source=source, target=target, weight=weight)
        dist = dists[target]
        return {
            "source": int(source),
            "target": int(target),
            "path": [int(x) for x in path],
            "distance": int(dist) if float(dist).is_integer() else round(float(dist), 2),
            "distances": clean_dists,
            "negative_cycle": False,
            "error": None,
        }
    except nx.NetworkXUnbounded:
        return {
            "source": int(source) if source is not None else 0,
            "target": int(target) if target is not None else 0,
            "path": [],
            "distance": float("-inf"),
            "distances": {},
            "negative_cycle": True,
            "error": "Detekován záporný cyklus — nejkratší cesty nejsou omezené."
        }
    except Exception as e:
        return {"negative_cycle": False, "error": str(e)}


def bellman_ford_steps(G: nx.Graph, source: int = None, target: int = None) -> dict:
    """
    Kroková verze Bellman-Fordova algoritmu pro interaktivní vizualizér.
    """
    try:
        nodes = sorted([int(n) for n in G.nodes()])
        if not nodes:
            return {"error": "Graf je prázdný."}
        if source is None or source not in nodes:
            source = nodes[0]
        if target is None or target not in nodes:
            target = nodes[-1]

        directed = G.is_directed()
        edges = []
        for u, v, d in G.edges(data=True):
            w = d.get("weight", 1)
            edges.append((int(u), int(v), w))
            if not directed:
                edges.append((int(v), int(u), w))

        dist = {n: float("inf") for n in nodes}
        parent = {n: None for n in nodes}
        dist[int(source)] = 0

        steps = []
        step_num = 0

        def current_tree_edges():
            res = []
            for n, p in parent.items():
                if p is not None:
                    res.append([int(p), int(n)])
            return res

        steps.append({
            "step": step_num,
            "action": "init",
            "edge": None,
            "weight": None,
            "description": f"Inicializace Bellman-Ford: dist[{source}] = 0, ostatní = ∞.",
            "selected_edges": [],
            "current_edge": None,
            "highlight_nodes": [int(source)],
        })
        step_num += 1

        n_nodes = len(nodes)
        for iteration in range(1, n_nodes):
            updated = False
            for u, v, w in edges:
                if dist[u] != float("inf"):
                    if dist[u] + w < dist[v]:
                        old = "∞" if dist[v] == float("inf") else dist[v]
                        dist[v] = dist[u] + w
                        parent[v] = u
                        updated = True
                        steps.append({
                            "step": step_num,
                            "action": "accept",
                            "edge": [u, v],
                            "weight": w,
                            "description": f"Iterace {iteration}: Relaxace hrany {u}→{v} (váha {w}). dist[{v}] snížena z {old} na {dist[v]}.",
                            "selected_edges": current_tree_edges(),
                            "current_edge": [u, v],
                            "highlight_nodes": [u, v],
                        })
                        step_num += 1
            if not updated:
                break

        # Kontrola záporného cyklu
        for u, v, w in edges:
            if dist[u] != float("inf") and dist[u] + w < dist[v]:
                steps.append({
                    "step": step_num,
                    "action": "reject",
                    "edge": [u, v],
                    "weight": w,
                    "description": f"Detekován záporný cyklus na hraně {u}→{v}!",
                    "selected_edges": current_tree_edges(),
                    "current_edge": [u, v],
                    "highlight_nodes": [u, v],
                })
                return {
                    "algorithm": "bellman_ford",
                    "algorithm_name": "Bellman-Fordův algoritmus",
                    "steps": steps,
                    "error": None,
                }

        # Rekonstrukce výsledné cesty do target
        final_edges = []
        path_nodes = []
        if dist[int(target)] != float("inf"):
            curr = int(target)
            visited_trace = set()
            while curr is not None and curr not in visited_trace:
                visited_trace.add(curr)
                path_nodes.append(curr)
                p = parent[curr]
                if p is not None:
                    final_edges.append([int(p), int(curr)])
                curr = p
            path_nodes.reverse()
            final_edges.reverse()
            desc = f"Hotovo! Nejkratší cesta z {source} do {target}: {' → '.join(map(str, path_nodes))} (délka {dist[int(target)]})."
        else:
            desc = f"Hotovo! Uzel {target} není z uzlu {source} dosažitelný."

        steps.append({
            "step": step_num,
            "action": "done",
            "edge": None,
            "weight": None,
            "description": desc,
            "selected_edges": final_edges if final_edges else current_tree_edges(),
            "current_edge": None,
            "highlight_nodes": path_nodes if path_nodes else [int(source)],
        })

        return {
            "algorithm": "bellman_ford",
            "algorithm_name": "Bellman-Fordův algoritmus",
            "steps": steps,
            "result_edges": final_edges,
            "error": None,
        }
    except Exception as e:
        return {"error": str(e)}


def graph_coloring(G: nx.Graph) -> dict:
    """
    Barvení grafu (Greedy / Welsh-Powell — strategie largest_first).

    Args:
        G: NetworkX graf

    Returns:
        dict: {
            "chromatic_number": int,
            "coloring": dict,
            "color_classes": dict,
            "error": str|None
        }
    """
    try:
        H = G.to_undirected() if G.is_directed() else G
        coloring_raw = nx.coloring.greedy_color(H, strategy="largest_first")
        coloring = {f"u{int(k)}": int(v) + 1 for k, v in sorted(coloring_raw.items())}
        num_colors = max(coloring.values()) if coloring else 0

        color_classes = {}
        for node_str, c in coloring.items():
            color_classes.setdefault(f"Barva {c}", []).append(node_str)

        return {
            "chromatic_number": num_colors,
            "coloring": coloring,
            "color_classes": color_classes,
            "error": None,
        }
    except Exception as e:
        return {"chromatic_number": 0, "coloring": {}, "color_classes": {}, "error": str(e)}


def euler_path(G: nx.Graph) -> dict:
    """
    Eulerovský tah a Eulerovská kružnice (sled obsahující každou hranu právě jednou).

    Args:
        G: NetworkX graf

    Returns:
        dict: {
            "has_euler_circuit": bool,
            "has_euler_path": bool,
            "circuit": list,
            "path": list,
            "error": str|None
        }
    """
    try:
        if G.number_of_edges() == 0:
            return {
                "has_euler_circuit": False,
                "has_euler_path": False,
                "circuit": [],
                "path": [],
                "error": "Graf neobsahuje žádné hrany."
            }

        has_circuit = nx.is_eulerian(G)
        has_path = nx.has_eulerian_path(G)

        circuit_edges = []
        path_edges = []

        if has_circuit:
            circuit_edges = [f"u{int(u)}→u{int(v)}" for u, v in nx.eulerian_circuit(G)]
            path_edges = circuit_edges
        elif has_path:
            path_edges = [f"u{int(u)}→u{int(v)}" for u, v in nx.eulerian_path(G)]

        return {
            "has_euler_circuit": bool(has_circuit),
            "has_euler_path": bool(has_path),
            "circuit": circuit_edges,
            "path": path_edges,
            "error": None,
        }
    except Exception as e:
        return {
            "has_euler_circuit": False,
            "has_euler_path": False,
            "circuit": [],
            "path": [],
            "error": str(e),
        }


def hamilton_path(G: nx.Graph) -> dict:
    """
    Hledání Hamiltonovské cesty a Hamiltonovské kružnice (prochází každý uzel právě jednou).
    Využívá backtracking s ořezáváním (pro grafy do 18 uzlů exaktně).

    Args:
        G: NetworkX graf

    Returns:
        dict: {
            "has_hamilton_cycle": bool,
            "has_hamilton_path": bool,
            "cycle": list,
            "path": list,
            "error": str|None
        }
    """
    try:
        nodes = sorted([int(n) for n in G.nodes()])
        n = len(nodes)
        if n == 0:
            return {"has_hamilton_cycle": False, "has_hamilton_path": False, "cycle": [], "path": [], "error": "Prázdný graf."}
        if n > 20:
            return {
                "has_hamilton_cycle": False,
                "has_hamilton_path": False,
                "cycle": [],
                "path": [],
                "error": "Exaktní test Hamiltonovské kružnice je z důvodu NP-úplnosti omezen na grafy do 20 uzlů."
            }

        adj = {u: sorted([int(v) for v in G.neighbors(u)]) for u in nodes}
        found_path = []
        found_cycle = []

        def backtrack(curr_path, visited):
            nonlocal found_path, found_cycle
            if len(curr_path) == n:
                if not found_path:
                    found_path = list(curr_path)
                # Zkontroluj uzavření do kružnice
                if curr_path[0] in adj[curr_path[-1]]:
                    found_cycle = list(curr_path) + [curr_path[0]]
                    return True
                return False

            last = curr_path[-1]
            for nxt in adj[last]:
                if nxt not in visited:
                    visited.add(nxt)
                    curr_path.append(nxt)
                    if backtrack(curr_path, visited):
                        return True
                    curr_path.pop()
                    visited.remove(nxt)
            return False

        for start_node in nodes:
            if backtrack([start_node], {start_node}):
                break

        return {
            "has_hamilton_cycle": bool(found_cycle),
            "has_hamilton_path": bool(found_path),
            "cycle": [f"u{x}" for x in found_cycle],
            "path": [f"u{x}" for x in found_path],
            "error": None,
        }
    except Exception as e:
        return {
            "has_hamilton_cycle": False,
            "has_hamilton_path": False,
            "cycle": [],
            "path": [],
            "error": str(e),
        }


def components_and_bridges(G: nx.Graph) -> dict:
    """
    Analýza souvislosti:
    - Pro neorientované grafy: souvislé komponenty, artikulace (kritické uzly) a mosty (kritické hrany).
    - Pro orientované grafy: silně souvislé komponenty (SCC — Tarjanův algoritmus) a slabě souvislé komponenty.
    """
    try:
        if G.is_directed():
            sccs = [sorted([f"u{int(x)}" for x in comp]) for comp in nx.strongly_connected_components(G)]
            sccs.sort(key=lambda c: (-len(c), c))
            wccs = [sorted([f"u{int(x)}" for x in comp]) for comp in nx.weakly_connected_components(G)]
            return {
                "is_directed": True,
                "strongly_connected_count": len(sccs),
                "strongly_connected_components": sccs,
                "weakly_connected_count": len(wccs),
                "articulation_points": [],
                "bridges": [],
                "error": None,
            }
        else:
            ccs = [sorted([f"u{int(x)}" for x in comp]) for comp in nx.connected_components(G)]
            ccs.sort(key=lambda c: (-len(c), c))
            articulations = sorted([f"u{int(x)}" for x in nx.articulation_points(G)])
            bridges = [f"u{int(u)}–u{int(v)}" for u, v in sorted(nx.bridges(G))]
            return {
                "is_directed": False,
                "connected_components_count": len(ccs),
                "connected_components": ccs,
                "articulation_points": articulations,
                "bridges": bridges,
                "error": None,
            }
    except Exception as e:
        return {"error": str(e)}

