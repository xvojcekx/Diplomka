"""
scenarios.py — Didaktický generátor slovních zadání a písemek

Generuje kontextová slovní zadání pro výuku teorie grafů (logistika, optické sítě,
kritická infrastruktura, projektové řízení apod.) a připravuje jak zadání pro studenty
(včetně předtištěných tabulek pro ruční výpočet), tak autorská vzorová řešení
s mezivýsledky pro vyučujícího.
"""

import networkx as nx
from typing import Dict, Any, List, Optional, Tuple
from solver import (
    shortest_path_dijkstra,
    minimum_spanning_tree,
    bellman_ford,
    components_and_bridges,
    ford_fulkerson_max_flow,
    topological_sort,
)


def node_to_letter(node_idx: int) -> str:
    """Převede číselný index uzlu (0, 1, ...) na písmenné označení (A, B, ..., Z, AA...)."""
    n = int(node_idx)
    if n < 26:
        return chr(65 + n)
    return chr(65 + (n // 26) - 1) + chr(65 + (n % 26))


def node_to_dual_label(node_idx: int) -> str:
    """Vrátí kombinované označení uzlu 'A (0)'."""
    return f"{node_to_letter(node_idx)} ({node_idx})"


def build_scenario_for_graph(
    graph_data: dict,
    scenario_type: str = "auto",
    source: Optional[int] = None,
    target: Optional[int] = None,
    mid: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Sestaví slovní zadání, předtištěnou tabulku pro studenta a autorské řešení pro daný graf.

    Typy scénářů:
    - dijkstra: Logistický rozvoz (nejkratší cesta)
    - dijkstra_stopover: Trasa s povinnou mezizastávkou bez opakování hran
    - kruskal: Návrh optické sítě (minimální kostra)
    - bellman_ford: Trasa se záporným ohodnocením (didaktická past)
    - bridges: Odolnost sítě a hledání kritických spojů (mosty a artikulace)
    - toposort: Harmonogram realizace projektu (DAG)
    - max_flow: Přepravní kapacita sítě (tok a minimální řez)
    """
    config = graph_data.get("config", {})
    props = graph_data.get("properties", {})
    node_count = props.get("node_count", 0)
    is_directed = config.get("directed", False)
    is_weighted = config.get("weighted", True)
    has_bridge_forced = config.get("force_bridge", False)

    # Automatická detekce vhodného scénáře, pokud není specifikován
    if scenario_type == "auto" or not scenario_type:
        if is_directed and config.get("acyclic", False):
            scenario_type = "toposort"
        elif is_directed and config.get("allow_negative_edge", False):
            scenario_type = "bellman_ford"
        elif has_bridge_forced:
            scenario_type = "bridges"
        elif not is_directed and is_weighted:
            scenario_type = "kruskal"
        elif is_directed and is_weighted:
            scenario_type = "dijkstra"
        else:
            scenario_type = "dijkstra"

    # Rekonstrukce grafu
    G = nx.DiGraph() if is_directed else nx.Graph()
    for i in range(node_count):
        G.add_node(i)
    for e in graph_data.get("edge_list", []):
        if "weight" in e and e["weight"] is not None:
            G.add_edge(e["source"], e["target"], weight=e["weight"])
        else:
            G.add_edge(e["source"], e["target"], weight=1)

    nodes_sorted = sorted(G.nodes())
    default_start = nodes_sorted[0] if nodes_sorted else 0
    default_end = nodes_sorted[-1] if len(nodes_sorted) >= 2 else default_start

    start_node = source if (source is not None and source in G.nodes()) else default_start
    end_node = target if (target is not None and target in G.nodes() and target != start_node) else default_end
    if start_node == end_node and len(nodes_sorted) >= 2:
        end_node = nodes_sorted[-1] if start_node != nodes_sorted[-1] else nodes_sorted[0]

    if scenario_type == "dijkstra_stopover":
        res = _scenario_dijkstra_stopover(G, graph_data, start_node, end_node, mid_node=mid)
    elif scenario_type == "dijkstra":
        res = _scenario_dijkstra(G, graph_data, start_node, end_node)
    elif scenario_type == "kruskal":
        res = _scenario_kruskal(G, graph_data)
    elif scenario_type == "bellman_ford":
        res = _scenario_bellman_ford(G, graph_data, start_node, end_node)
    elif scenario_type == "bridges":
        res = _scenario_bridges(G, graph_data)
    elif scenario_type == "toposort":
        res = _scenario_toposort(G, graph_data)
    elif scenario_type == "max_flow":
        res = _scenario_max_flow(G, graph_data, start_node, end_node)
    else:
        res = _scenario_dijkstra(G, graph_data, start_node, end_node)

    res["source_node"] = start_node
    res["target_node"] = end_node
    res.setdefault("mid_node", mid)
    return res


# ============================================================================
# POMOCNÉ VÝPOČTY PRO MEZIVÝSLEDKY A BEZHRANOVĚ DISJUNKTNÍ TRASY
# ============================================================================

def _compute_all_shortest_distances(G: nx.Graph, start_node: int) -> Tuple[Dict[int, Any], Dict[int, Optional[int]]]:
    """Vrátí slovník nejkratších vzdáleností d(v) a předchůdců p(v) ze start_node do všech uzlů."""
    distances: Dict[int, Any] = {n: "∞" for n in sorted(G.nodes())}
    predecessors: Dict[int, Optional[int]] = {n: None for n in sorted(G.nodes())}
    distances[start_node] = 0
    try:
        pred_dict, dist_dict = nx.bellman_ford_predecessor_and_distance(G, start_node, weight="weight")
        for n, d in dist_dict.items():
            distances[n] = d
        for n, p_list in pred_dict.items():
            if p_list:
                predecessors[n] = p_list[0]
    except Exception:
        pass
    return distances, predecessors


def _find_edge_disjoint_stopover_path(
    G: nx.Graph, start_node: int, mid_node: int, end_node: int
) -> Dict[str, Any]:
    """
    Nalezne nejkratší sled ze start_node přes mid_node do end_node,
    který neprojde žádnou hranu grafu dvakrát.
    """
    best_total = None
    best_p1: List[int] = []
    best_p2: List[int] = []
    best_len1 = 0
    best_len2 = 0

    try:
        # Prohledáme jednoduché cesty S -> M seřazené podle délky
        simple_paths_s_m = list(nx.all_simple_paths(G, start_node, mid_node))
    except nx.NetworkXException:
        simple_paths_s_m = []

    def path_weight(graph: nx.Graph, p: List[int]) -> int:
        return sum(graph[p[i]][p[i + 1]].get("weight", 1) for i in range(len(p) - 1))

    simple_paths_s_m.sort(key=lambda p: path_weight(G, p))

    def _search_disjoint(avoid_vertices: bool):
        b_tot = None
        b_p1: List[int] = []
        b_p2: List[int] = []
        b_l1 = 0
        b_l2 = 0
        for p1 in simple_paths_s_m[:40]:
            if avoid_vertices and end_node in p1[:-1]:
                continue
            len1 = path_weight(G, p1)
            if b_tot is not None and len1 >= b_tot:
                break
            G_rem = G.copy()
            for i in range(len(p1) - 1):
                u, v = p1[i], p1[i + 1]
                if G_rem.has_edge(u, v):
                    G_rem.remove_edge(u, v)
            if avoid_vertices:
                for visited_u in p1[:-1]:
                    if visited_u in G_rem:
                        G_rem.remove_node(visited_u)
            try:
                p2 = nx.shortest_path(G_rem, mid_node, end_node, weight="weight")
                len2 = path_weight(G_rem, p2)
                total = len1 + len2
                if b_tot is None or total < b_tot:
                    b_tot = total
                    b_p1 = p1
                    b_p2 = p2
                    b_l1 = len1
                    b_l2 = len2
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue
        return b_tot, b_p1, b_p2, b_l1, b_l2

    # Nejprve preferuj vrcholově prostou cestu S -> M -> T (bez vracení přes již navštívené uzly),
    # teprve pokud neexistuje, povol opakování uzlu při zachování hranové disjunktnosti.
    best_total, best_p1, best_p2, best_len1, best_len2 = _search_disjoint(avoid_vertices=True)
    if best_total is None:
        best_total, best_p1, best_p2, best_len1, best_len2 = _search_disjoint(avoid_vertices=False)

    if best_total is not None:
        return {
            "valid": True,
            "edge_disjoint": True,
            "p1": best_p1,
            "p2": best_p2,
            "len1": best_len1,
            "len2": best_len2,
            "total_distance": best_total,
            "full_path": best_p1 + best_p2[1:],
        }

    # Fallback pokud v grafu neexistuje hranově disjunktní cesta (např. mezizastávka za mostem)
    sol1 = shortest_path_dijkstra(G, start_node, mid_node)
    sol2 = shortest_path_dijkstra(G, mid_node, end_node)
    p1 = sol1.get("path") or []
    p2 = sol2.get("path") or []
    d1 = sol1.get("distance") or 0
    d2 = sol2.get("distance") or 0
    return {
        "valid": bool(p1 and p2),
        "edge_disjoint": False,
        "p1": p1,
        "p2": p2,
        "len1": d1,
        "len2": d2,
        "total_distance": (d1 + d2) if (p1 and p2) else None,
        "full_path": (p1 + p2[1:]) if (p1 and p2) else [],
    }


# ============================================================================
# JEDNOTLIVÉ SCÉNÁŘE
# ============================================================================

def _scenario_dijkstra(G: nx.Graph, graph_data: dict, start_node: int, end_node: int) -> dict:
    s_lbl = node_to_letter(start_node)
    t_lbl = node_to_letter(end_node)
    nodes_sorted = sorted(G.nodes())

    sol = shortest_path_dijkstra(G, start_node, end_node)
    path = sol.get("path") or []
    path_lbls = [node_to_letter(n) for n in path]
    distance = sol.get("distance")

    distances, predecessors = _compute_all_shortest_distances(G, start_node)

    # Kontrola jednoznačnosti nejkratší cesty
    alt_paths_count = 0
    if distance is not None and path:
        try:
            for p in nx.all_shortest_paths(G, start_node, end_node, weight="weight"):
                alt_paths_count += 1
        except Exception:
            alt_paths_count = 1

    uniqueness_text = (
        "Jednoznačná (existuje právě 1 nejkratší cesta)"
        if alt_paths_count <= 1
        else f"Víceznačná (existují {alt_paths_count} různé nejkratší cesty stejné délky {distance})"
    )

    story = (
        f"Logistická společnost plánuje expresní přepravu zásilky z centrálního distribučního skladu "
        f"ve městě <strong>{s_lbl} ({start_node})</strong> do cílového depa ve městě <strong>{t_lbl} ({end_node})</strong>. "
        f"Jednotlivá města odpovídají vrcholům grafu, silniční tahy hranám a čísla na hranách značí "
        f"dobu jízdy v minutách."
    )
    questions = [
        f"Pomocí <strong>Dijkstrova algoritmu</strong> nalezněte nejkratší časovou trasu z města <strong>{s_lbl}</strong> do města <strong>{t_lbl}</strong>.",
        "Vyplňte předtištěnou tabulku výsledných vzdáleností <code>d(v)</code> a předchůdců <code>p(v)</code> pro všechny vrcholy grafu.",
        f"Vypište výslednou posloupnost měst na trase {s_lbl} → {t_lbl} a celkovou dobu jízdy v minutách.",
        "Uveďte, zda je nalezená nejkratší cesta jednoznačná, nebo zda existuje alternativní trasa o stejné délce."
    ]

    # Předtištěná tabulka pro studenta
    header_cells = "".join(f"<th class='text-center'>{node_to_letter(n)} ({n})</th>" for n in nodes_sorted)
    empty_d_cells = "".join(
        f"<td class='text-center'>{'0' if n == start_node else '&nbsp;'}</td>" for n in nodes_sorted
    )
    empty_p_cells = "".join(
        f"<td class='text-center'>{'—' if n == start_node else '&nbsp;'}</td>" for n in nodes_sorted
    )
    student_table_html = (
        f"<div class='small fw-bold text-muted text-uppercase mb-1'>Tabulka pro zápis výsledků Dijkstrova algoritmu (start: {s_lbl}):</div>"
        f"<table class='table table-bordered table-sm mb-3'>"
        f"<thead class='table-light'><tr><th style='width: 160px;'>Vrchol <em>v</em></th>{header_cells}</tr></thead>"
        f"<tbody>"
        f"<tr><td class='fw-semibold'>Vzdálenost <em>d(v)</em></td>{empty_d_cells}</tr>"
        f"<tr><td class='fw-semibold'>Předchůdce <em>p(v)</em></td>{empty_p_cells}</tr>"
        f"</tbody></table>"
    )

    # Autorská tabulka pro učitele
    solved_d_cells = "".join(f"<td class='text-center fw-bold'>{distances[n]}</td>" for n in nodes_sorted)
    solved_p_cells = "".join(
        f"<td class='text-center'>{node_to_letter(predecessors[n]) if predecessors[n] is not None else '—'}</td>"
        for n in nodes_sorted
    )
    teacher_table_html = (
        f"<table class='table table-bordered table-sm bg-white mt-2 mb-2'>"
        f"<thead class='table-light'><tr><th>Vrchol <em>v</em></th>{header_cells}</tr></thead>"
        f"<tbody>"
        f"<tr><td class='fw-semibold'>Minimální vzdálenost <em>d(v)</em></td>{solved_d_cells}</tr>"
        f"<tr><td class='fw-semibold'>Předchůdce <em>p(v)</em></td>{solved_p_cells}</tr>"
        f"</tbody></table>"
    )

    path_str = " → ".join(path_lbls) if path_lbls else "Cesta neexistuje"
    dist_str = f"{distance} minut" if distance is not None else "Nedosažitelné (∞)"

    teacher_solution = (
        f"<p class='mb-1'><strong>1. Výsledná nejkratší cesta ({s_lbl} → {t_lbl}):</strong> <span class='badge bg-success fs-6'>{path_str}</span></p>"
        f"<p class='mb-2'><strong>2. Celková doba jízdy (délka cesty):</strong> <strong>{dist_str}</strong></p>"
        f"<p class='mb-1'><strong>3. Kontrolní tabulka vzdáleností ze startu {s_lbl} do všech vrcholů:</strong></p>"
        f"{teacher_table_html}"
        f"<p class='mb-0'><strong>4. Jednoznačnost řešení:</strong> {uniqueness_text}.</p>"
    )

    return {
        "scenario_type": "dijkstra",
        "title": f"Optimalizace doručovací trasy ({s_lbl} → {t_lbl})",
        "algorithm_badge": "Dijkstrův algoritmus",
        "story": story,
        "questions": questions,
        "student_table_html": student_table_html,
        "teacher_solution": teacher_solution,
        "target_nodes": f"{s_lbl} → {t_lbl}",
        "solution_summary": f"Cesta: {path_str}, Délka: {distance if distance is not None else '∞'}"
    }


def _scenario_dijkstra_stopover(
    G: nx.Graph,
    graph_data: dict,
    start_node: int,
    end_node: int,
    mid_node: Optional[int] = None,
) -> dict:
    nodes_sorted = sorted(G.nodes())
    direct_sol = shortest_path_dijkstra(G, start_node, end_node)
    direct_path = direct_sol.get("path") or []
    direct_len = direct_sol.get("distance")

    # Pokud není mid_node zadán, vybereme uzel mimo přímou nejkratší cestu,
    # pro který existuje hranově disjunktní trasa S -> M -> T
    if mid_node is None or mid_node not in G.nodes() or mid_node in (start_node, end_node):
        candidates_off_direct = [
            n for n in nodes_sorted
            if n not in (start_node, end_node) and n not in direct_path
        ]
        candidates_all = [n for n in nodes_sorted if n not in (start_node, end_node)]
        search_order = candidates_off_direct + [n for n in candidates_all if n not in candidates_off_direct]

        chosen_mid = search_order[0] if search_order else start_node
        found_vertex_simple = False
        for cand in search_order:
            test_res = _find_edge_disjoint_stopover_path(G, start_node, cand, end_node)
            if test_res["valid"] and test_res["edge_disjoint"]:
                fp = test_res["full_path"]
                if len(fp) == len(set(fp)):
                    chosen_mid = cand
                    found_vertex_simple = True
                    break
        if not found_vertex_simple:
            for cand in search_order:
                test_res = _find_edge_disjoint_stopover_path(G, start_node, cand, end_node)
                if test_res["valid"] and test_res["edge_disjoint"]:
                    chosen_mid = cand
                    break
        mid_node = chosen_mid

    stopover_res = _find_edge_disjoint_stopover_path(G, start_node, mid_node, end_node)
    p1 = stopover_res["p1"]
    p2 = stopover_res["p2"]
    len1 = stopover_res["len1"]
    len2 = stopover_res["len2"]
    total_len = stopover_res["total_distance"]
    full_path = stopover_res["full_path"]
    is_disjoint = stopover_res["edge_disjoint"]

    s_lbl = node_to_letter(start_node)
    m_lbl = node_to_letter(mid_node)
    t_lbl = node_to_letter(end_node)
    full_path_lbls = [node_to_letter(n) for n in full_path]

    story = (
        f"Doručovací dodávka vyjíždí z centrálního skladu <strong>{s_lbl} ({start_node})</strong> a musí dovézt zboží "
        f"do cílové pobočky <strong>{t_lbl} ({end_node})</strong>. Cestou se však musí povinně zastavit na překladišti "
        f"<strong>{m_lbl} ({mid_node})</strong> k naložení palet. Z důvodu uzavírek a jednosměrného provozu "
        f"<strong>nesmí řidič žádný silniční úsek (hranu) projet dvakrát</strong>."
    )
    questions = [
        f"Nalezněte nejkratší trasu z <strong>{s_lbl}</strong> do <strong>{t_lbl}</strong> s povinnou mezizastávkou v uzlu <strong>{m_lbl}</strong> bez opakování hran.",
        f"Zapište zvlášť 1. etapu ({s_lbl} → {m_lbl}) a 2. etapu ({m_lbl} → {t_lbl}) a jejich dílčí časy jízdy.",
        f"Porovnejte nalezenou trasu s přímou nejkratší cestou {s_lbl} → {t_lbl} (bez mezizastávky) a vyčíslete časové zdržení."
    ]

    student_table_html = (
        "<div class='small fw-bold text-muted text-uppercase mb-1'>Tabulka pro porovnání etap trasy:</div>"
        "<table class='table table-bordered table-sm mb-3'>"
        "<thead class='table-light'><tr><th>Úsek trasy</th><th>Posloupnost uzlů</th><th>Doba jízdy (min)</th></tr></thead>"
        "<tbody>"
        f"<tr><td>1. etapa ({s_lbl} → {m_lbl})</td><td>&nbsp;</td><td>&nbsp;</td></tr>"
        f"<tr><td>2. etapa ({m_lbl} → {t_lbl}, bez použitých hran)</td><td>&nbsp;</td><td>&nbsp;</td></tr>"
        f"<tr><td class='fw-bold'>Celková trasa ({s_lbl} → {m_lbl} → {t_lbl})</td><td>&nbsp;</td><td>&nbsp;</td></tr>"
        f"<tr><td>Přímá trasa bez zastávky ({s_lbl} → {t_lbl}) / Zdržení</td><td>&nbsp;</td><td>&nbsp;</td></tr>"
        "</tbody></table>"
    )

    delay = (total_len - direct_len) if (total_len is not None and direct_len is not None) else "—"
    disjoint_badge = (
        "<span class='badge bg-success'>Splněno — žádná hrana se neopakuje</span>"
        if is_disjoint
        else "<span class='badge bg-warning text-dark'>Pozor: uzel je za mostem, nutno použít hranu opakovaně</span>"
    )

    teacher_solution = (
        f"<p class='mb-1'><strong>1. etapa ({s_lbl} → {m_lbl}):</strong> {' → '.join(node_to_letter(n) for n in p1)} (délka: <strong>{len1} min</strong>)</p>"
        f"<p class='mb-1'><strong>2. etapa ({m_lbl} → {t_lbl}):</strong> {' → '.join(node_to_letter(n) for n in p2)} (délka: <strong>{len2} min</strong>)</p>"
        f"<p class='mb-1'><strong>Celková trasa přes {m_lbl}:</strong> <span class='badge bg-success fs-6'>{' → '.join(full_path_lbls)}</span> "
        f"(celková délka: <strong>{total_len} min</strong>) • {disjoint_badge}</p>"
        f"<p class='mb-0'><strong>Přímá trasa ({s_lbl} → {t_lbl} bez zastávky):</strong> {' → '.join(node_to_letter(n) for n in direct_path)} "
        f"(délka: <strong>{direct_len} min</strong>) ⇒ <strong>Časové zdržení za zajížďku: +{delay} min</strong>.</p>"
    )

    return {
        "scenario_type": "dijkstra_stopover",
        "mid_node": mid_node,
        "title": f"Trasa s povinnou mezizastávkou ({s_lbl} → {m_lbl} → {t_lbl})",
        "algorithm_badge": "Dijkstra s mezizastávkou (bez opakování hran)",
        "story": story,
        "questions": questions,
        "student_table_html": student_table_html,
        "teacher_solution": teacher_solution,
        "target_nodes": f"{s_lbl} → {m_lbl} → {t_lbl}",
        "solution_summary": f"Trasa: {' → '.join(full_path_lbls)}, Délka: {total_len} (zdržení +{delay})"
    }


def _scenario_kruskal(G: nx.Graph, graph_data: dict) -> dict:
    mst_res = minimum_spanning_tree(G)
    tree_edges = mst_res.get("tree_edges") or []
    total_w = mst_res.get("total_weight", 0)

    mst_edge_strs = [
        f"{node_to_letter(e['source'])}–{node_to_letter(e['target'])} ({e.get('weight', 1)})"
        for e in tree_edges
    ]

    # Sestavíme kompletní krok po kroku tabulku všech hran seřazených podle váhy (Kruskal)
    all_edges_sorted = sorted(
        [(u, v, d.get("weight", 1)) for u, v, d in G.edges(data=True)],
        key=lambda x: (x[2], min(x[0], x[1]), max(x[0], x[1])),
    )
    uf_parent = {n: n for n in G.nodes()}

    def find(x: int) -> int:
        while uf_parent[x] != x:
            uf_parent[x] = uf_parent[uf_parent[x]]
            x = uf_parent[x]
        return x

    rows_html = []
    for idx, (u, v, w) in enumerate(all_edges_sorted, start=1):
        ru, rv = find(u), find(v)
        if ru != rv:
            uf_parent[ru] = rv
            status_html = "<span class='text-success fw-bold'>✓ Zařazena do kostry</span>"
        else:
            status_html = "<span class='text-danger'>✗ Zamítnuta (tvoří cyklus)</span>"
        rows_html.append(
            f"<tr><td class='text-center'>{idx}.</td>"
            f"<td class='fw-semibold'>{node_to_letter(u)}–{node_to_letter(v)} ({u}–{v})</td>"
            f"<td class='text-center'>{w}</td>"
            f"<td>{status_html}</td></tr>"
        )

    weights_list = [w for _, _, w in all_edges_sorted]
    has_unique_weights = len(weights_list) == len(set(weights_list))
    uniqueness_note = (
        "Všechny váhy hran v grafu jsou navzájem různé ⇒ minimální kostra je zaručeně jednoznačná."
        if has_unique_weights
        else "Některé hrany mají shodnou váhu ⇒ může existovat více minimálních koster se stejnou celkovou cenou."
    )

    story = (
        "Telekomunikační společnost připravuje výstavbu vysokorychlostní optické infrastruktury "
        "propojující univerzitní kampusy a výzkumná centra. Každý uzel představuje jednu lokalitu, "
        "hrany představují možné trasy pro položení kabelovodů a váhy hran značí investiční náklady v milionech Kč. "
        "Cílem je propojit všechny lokality navzájem tak, aby celkové náklady na položení kabelů byly minimální."
    )
    questions = [
        "Pomocí <strong>Kruskalova algoritmu</strong> navrhněte optimální schéma propojení všech lokalit (minimální kostru grafu).",
        "Seřaďte hrany vzestupně podle nákladů a pro každou hranu rozhodněte, zda bude do kostry zařazena, nebo zamítnuta z důvodu vytvoření cyklu.",
        f"Uveďte počet vybraných hran pro graf s {G.number_of_nodes()} lokalitami a spočítejte celkové investiční náklady v mil. Kč.",
        "Rozhodněte, zda je nalezená minimální kostra jednoznačná, a své tvrzení zdůvodněte."
    ]

    target_edge_count = max(0, G.number_of_nodes() - 1)
    empty_rows = "".join(
        f"<tr><td class='text-center'>{i}.</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td></tr>"
        for i in range(1, target_edge_count + 1)
    )
    student_table_html = (
        f"<div class='small fw-bold text-muted text-uppercase mb-1'>Tabulka pro výběr {target_edge_count} hran minimální kostry:</div>"
        "<table class='table table-bordered table-sm mb-3'>"
        "<thead class='table-light'><tr><th style='width:50px;'>Poř.</th><th>Hrana (u–v)</th><th>Cena (mil. Kč)</th><th>Poznámka / Kontrola cyklu</th></tr></thead>"
        f"<tbody>{empty_rows}</tbody></table>"
    )

    teacher_solution = (
        f"<p class='mb-1'><strong>1. Vybrané hrany minimální kostry ({len(tree_edges)} hran):</strong> "
        f"<span class='badge bg-success fs-6'>{', '.join(mst_edge_strs)}</span></p>"
        f"<p class='mb-2'><strong>2. Celkové investiční náklady (součet vah):</strong> <strong>{total_w} mil. Kč</strong></p>"
        f"<p class='mb-1'><strong>3. Kompletní rozhodovací tabulka Kruskalova algoritmu:</strong></p>"
        f"<table class='table table-bordered table-sm bg-white mt-1 mb-2'>"
        f"<thead class='table-light'><tr><th>Poř.</th><th>Hrana</th><th>Váha</th><th>Rozhodnutí algoritmu</th></tr></thead>"
        f"<tbody>{''.join(rows_html)}</tbody></table>"
        f"<p class='mb-0'><strong>4. Jednoznačnost:</strong> {uniqueness_note}</p>"
    )

    return {
        "scenario_type": "kruskal",
        "title": "Výstavba páteřní optické sítě (Minimální kostra)",
        "algorithm_badge": "Kruskalův algoritmus (MST)",
        "story": story,
        "questions": questions,
        "student_table_html": student_table_html,
        "teacher_solution": teacher_solution,
        "target_nodes": f"{G.number_of_nodes()} lokalit ({target_edge_count} hran kostry)",
        "solution_summary": f"Cena MST: {total_w} mil. Kč, Hran: {len(tree_edges)}"
    }


def _scenario_bellman_ford(G: nx.Graph, graph_data: dict, start_node: int, end_node: int) -> dict:
    s_lbl = node_to_letter(start_node)
    t_lbl = node_to_letter(end_node)
    nodes_sorted = sorted(G.nodes())

    sol = bellman_ford(G, start_node, end_node)
    path = sol.get("path") or []
    path_lbls = [node_to_letter(n) for n in path]
    distance = sol.get("distance")
    has_neg_cycle = sol.get("has_negative_cycle", False)

    distances, predecessors = _compute_all_shortest_distances(G, start_node)
    neg_edges = [
        f"{node_to_letter(u)} → {node_to_letter(v)} (váha {d.get('weight', 0)})"
        for u, v, d in G.edges(data=True)
        if d.get("weight", 0) < 0
    ]

    story = (
        f"Mezinárodní fintech společnost převádí kapitál mezi trhy <strong>{s_lbl} ({start_node})</strong> až "
        f"<strong>{t_lbl} ({end_node})</strong>. Většina transakcí je zatížena kladným poplatkem, avšak některé trhy "
        f"nabízejí dotované pobídky se záporným poplatkem (záporná váha hrany: {', '.join(neg_edges) if neg_edges else 'viz graf'}). "
        f"Cílem je převést prostředky z trhu <strong>{s_lbl}</strong> na trh <strong>{t_lbl}</strong> s nejnižším možným celkovým poplatkem."
    )
    questions = [
        "Vysvětlete, proč v tomto grafu <strong>nelze spolehlivě použít Dijkstrův algoritmus</strong>.",
        f"Aplikujte <strong>Bellmanův-Fordův algoritmus</strong> pro nalezení nejvýhodnějšího převodu z {s_lbl} do {t_lbl} a vyplňte tabulku výsledných hodnot <code>d(v)</code>.",
        f"Uveďte, kolik relaxačních iterací provádí algoritmus pro graf s {G.number_of_nodes()} uzly a jak odhalí případný záporný cyklus.",
        f"Vypište optimální posloupnost trhů z {s_lbl} do {t_lbl} a výsledný součet poplatků."
    ]

    header_cells = "".join(f"<th class='text-center'>{node_to_letter(n)} ({n})</th>" for n in nodes_sorted)
    empty_d_cells = "".join(
        f"<td class='text-center'>{'0' if n == start_node else '&nbsp;'}</td>" for n in nodes_sorted
    )
    empty_p_cells = "".join(
        f"<td class='text-center'>{'—' if n == start_node else '&nbsp;'}</td>" for n in nodes_sorted
    )
    student_table_html = (
        f"<div class='small fw-bold text-muted text-uppercase mb-1'>Tabulka vzdáleností po skončení Bellmanova-Fordova algoritmu (start: {s_lbl}):</div>"
        f"<table class='table table-bordered table-sm mb-3'>"
        f"<thead class='table-light'><tr><th style='width: 160px;'>Vrchol <em>v</em></th>{header_cells}</tr></thead>"
        f"<tbody>"
        f"<tr><td class='fw-semibold'>Náklady <em>d(v)</em></td>{empty_d_cells}</tr>"
        f"<tr><td class='fw-semibold'>Předchůdce <em>p(v)</em></td>{empty_p_cells}</tr>"
        f"</tbody></table>"
    )

    solved_d_cells = "".join(f"<td class='text-center fw-bold'>{distances[n]}</td>" for n in nodes_sorted)
    solved_p_cells = "".join(
        f"<td class='text-center'>{node_to_letter(predecessors[n]) if predecessors[n] is not None else '—'}</td>"
        for n in nodes_sorted
    )
    teacher_table_html = (
        f"<table class='table table-bordered table-sm bg-white mt-1 mb-2'>"
        f"<thead class='table-light'><tr><th>Vrchol <em>v</em></th>{header_cells}</tr></thead>"
        f"<tbody>"
        f"<tr><td class='fw-semibold'>Minimální náklady <em>d(v)</em></td>{solved_d_cells}</tr>"
        f"<tr><td class='fw-semibold'>Předchůdce <em>p(v)</em></td>{solved_p_cells}</tr>"
        f"</tbody></table>"
    )

    path_str = " → ".join(path_lbls) if path_lbls else "Cesta neexistuje"
    teacher_solution = (
        f"<p class='mb-1'><strong>1. Proč selhává Dijkstra:</strong> Graf obsahuje záporné hrany ({', '.join(neg_edges) if neg_edges else 'záporné ohodnocení'}). "
        f"Dijkstrův hladový výběr předpokládá nezáporné váhy — po uzavření vrcholu by již neprovedl dodatečnou relaxaci přes zápornou hranu.</p>"
        f"<p class='mb-1'><strong>2. Výsledná optimální trasa ({s_lbl} → {t_lbl}):</strong> <span class='badge bg-success fs-6'>{path_str}</span> "
        f"(celkové náklady: <strong>{distance if distance is not None else '∞'}</strong>)</p>"
        f"<p class='mb-1'><strong>3. Výsledné hodnoty <em>d(v)</em> po {G.number_of_nodes() - 1} iteracích:</strong></p>"
        f"{teacher_table_html}"
        f"<p class='mb-0'><strong>4. Záporný cyklus:</strong> {'Detekován záporný cyklus!' if has_neg_cycle else f'V {G.number_of_nodes()}. kontrolním kroku již nedochází ke snížení d(v), graf záporný cyklus neobsahuje.'}</p>"
    )

    return {
        "scenario_type": "bellman_ford",
        "title": f"Finanční arbitráž a záporné poplatky ({s_lbl} → {t_lbl})",
        "algorithm_badge": "Bellmanův-Fordův algoritmus (Záporné hrany)",
        "story": story,
        "questions": questions,
        "student_table_html": student_table_html,
        "teacher_solution": teacher_solution,
        "target_nodes": f"{s_lbl} → {t_lbl}",
        "solution_summary": f"Cesta: {path_str}, Náklady: {distance if distance is not None else '∞'}"
    }


def _scenario_bridges(G: nx.Graph, graph_data: dict) -> dict:
    G_undir = G.to_undirected() if G.is_directed() else G
    raw_bridges = sorted(tuple(sorted(e)) for e in nx.bridges(G_undir))
    raw_arts = sorted(nx.articulation_points(G_undir))

    bridge_strs = [f"{node_to_letter(u)}–{node_to_letter(v)} ({u}–{v})" for u, v in raw_bridges]
    art_strs = [f"{node_to_letter(n)} ({n})" for n in raw_arts]

    # Navrhneme konkrétní záložní hranu pro odstranění mostu (spojení listových/vzdálených komponent)
    backup_suggestion = "Síť je již 2-souvislá."
    if raw_bridges:
        u_b, v_b = raw_bridges[0]
        G_temp = G_undir.copy()
        G_temp.remove_edge(u_b, v_b)
        comps = [ sorted(list(c)) for c in nx.connected_components(G_temp) ]
        if len(comps) >= 2:
            cand_a = next((x for x in comps[0] if x != u_b and x != v_b), comps[0][0])
            cand_b = next((x for x in comps[1] if x != u_b and x != v_b), comps[1][0])
            backup_suggestion = (
                f"Přidat záložní linku např. mezi uzly <strong>{node_to_letter(cand_a)} ({cand_a})</strong> "
                f"a <strong>{node_to_letter(cand_b)} ({cand_b})</strong>, čímž se vytvoří uzavřený okruh přes most."
            )

    story = (
        "Bezpečnostní audit páteřní datové sítě má za cíl odhalit kritická zranitelná místa infrastruktury "
        "(tzv. Single Point of Failure). Vrcholy představují datová centra, hrany optické trasy. "
        "Výpadek kritického uzlu nebo přerušení kritického kabelu způsobí rozpad sítě na izolované podsítě."
    )
    questions = [
        "Definujte pojmy <strong>most</strong> a <strong>artikulace (artikulační bod)</strong> v neorientovaném grafu.",
        "Vypište všechny <strong>mosty</strong> v zobrazené síti (hrany, jejichž odebrání zvýší počet komponent souvislosti).",
        "Vypište všechny <strong>artikulační uzly</strong> (vrcholy, jejichž výpadek rozdělí síť).",
        "Navrhněte konkrétní novou záložní hranu <code>(u, v)</code>, jejíž přidání odstraní kritický most a zvýší odolnost sítě."
    ]

    student_table_html = (
        "<div class='small fw-bold text-muted text-uppercase mb-1'>Tabulka identifikovaných kritických prvků sítě:</div>"
        "<table class='table table-bordered table-sm mb-3'>"
        "<thead class='table-light'><tr><th style='width:35%;'>Kritické spoje (Mosty)</th><th style='width:35%;'>Kritické uzly (Artikulace)</th><th>Navržená záložní linka</th></tr></thead>"
        "<tbody><tr style='height: 48px;'><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td></tr></tbody></table>"
    )

    teacher_solution = (
        f"<p class='mb-1'><strong>1. Nalezené mosty ({len(raw_bridges)}):</strong> "
        f"<span class='badge bg-danger fs-6'>{', '.join(bridge_strs) if bridge_strs else 'Žádný most'}</span></p>"
        f"<p class='mb-1'><strong>2. Artikulační uzly ({len(raw_arts)}):</strong> "
        f"<span class='badge bg-warning text-dark fs-6'>{', '.join(art_strs) if art_strs else 'Žádná artikulace'}</span></p>"
        f"<p class='mb-0'><strong>3. Návrh zabezpečení (redundance):</strong> {backup_suggestion}</p>"
    )

    return {
        "scenario_type": "bridges",
        "title": "Analýza zranitelnosti komunikační sítě (Mosty a artikulace)",
        "algorithm_badge": "Strukturální analýza (Mosty & Artikulace)",
        "story": story,
        "questions": questions,
        "student_table_html": student_table_html,
        "teacher_solution": teacher_solution,
        "target_nodes": f"{len(raw_bridges)} mostů, {len(raw_arts)} artikulací",
        "solution_summary": f"Mosty: {', '.join(bridge_strs) if bridge_strs else '0'}, Artikulace: {', '.join(art_strs) if art_strs else '0'}"
    }


def _scenario_toposort(G: nx.DiGraph, graph_data: dict) -> dict:
    topo_res = topological_sort(G)
    order = topo_res.get("order") or []
    order_lbls = [node_to_letter(n) for n in order]
    nodes_sorted = sorted(G.nodes())

    in_degrees = {n: G.in_degree(n) for n in nodes_sorted}
    out_degrees = {n: G.out_degree(n) for n in nodes_sorted}

    story = (
        f"Projektový manažer řídí nasazení nového informačního systému. Projekt sestává z dílčích etap "
        f"reprezentovaných uzly <strong>{', '.join(node_to_letter(n) for n in nodes_sorted)}</strong>. "
        f"Orientované hrany <code>u → v</code> představují technologické návaznosti — činnost <code>v</code> "
        f"může začít teprve tehdy, když jsou dokončeny všechny činnosti, z nichž do <code>v</code> vede šipka."
    )
    questions = [
        "Uveďte nutnou a postačující podmínku, kterou musí orientovaný graf splňovat, aby připouštěl topologické uspořádání.",
        "Pro každý uzel určete jeho počáteční vstupní stupeň <code>deg⁻(v)</code> (počet bezprostředních prerekvizit).",
        "Pomocí <strong>Kahnova algoritmu</strong> (postupné odebírání uzlů s nulovým vstupním stupněm) sestavte platný lineární harmonogram prací.",
        "Rozhodněte, zda v některém kroku algoritmu existovalo více uzlů s nulovým vstupním stupněm současně (a zda je tedy harmonogram víceznačný)."
    ]

    header_cells = "".join(f"<th class='text-center'>{node_to_letter(n)} ({n})</th>" for n in nodes_sorted)
    empty_indeg = "".join("<td class='text-center'>&nbsp;</td>" for _ in nodes_sorted)
    student_table_html = (
        "<div class='small fw-bold text-muted text-uppercase mb-1'>Tabulka vstupních stupňů uzlů deg⁻(v) před spuštěním Kahnova algoritmu:</div>"
        f"<table class='table table-bordered table-sm mb-3'>"
        f"<thead class='table-light'><tr><th style='width: 170px;'>Činnost (Uzel)</th>{header_cells}</tr></thead>"
        f"<tbody><tr><td class='fw-semibold'>Vstupní stupeň <em>deg⁻(v)</em></td>{empty_indeg}</tr></tbody></table>"
    )

    solved_indeg = "".join(f"<td class='text-center fw-bold'>{in_degrees[n]}</td>" for n in nodes_sorted)
    solved_outdeg = "".join(f"<td class='text-center'>{out_degrees[n]}</td>" for n in nodes_sorted)
    teacher_table_html = (
        f"<table class='table table-bordered table-sm bg-white mt-1 mb-2'>"
        f"<thead class='table-light'><tr><th>Uzel <em>v</em></th>{header_cells}</tr></thead>"
        f"<tbody>"
        f"<tr><td class='fw-semibold'>Vstupní stupeň <em>deg⁻(v)</em></td>{solved_indeg}</tr>"
        f"<tr><td class='fw-semibold'>Výstupní stupeň <em>deg⁺(v)</em></td>{solved_outdeg}</tr>"
        f"</tbody></table>"
    )

    order_str = " → ".join(order_lbls) if order_lbls else "Graf obsahuje cyklus (nelze topologicky seřadit)"
    teacher_solution = (
        f"<p class='mb-1'><strong>1. Podmínka existence:</strong> Graf musí být orientovaný acyklický graf (DAG — <em>Directed Acyclic Graph</em>).</p>"
        f"<p class='mb-1'><strong>2. Počáteční stupně vrcholů:</strong></p>"
        f"{teacher_table_html}"
        f"<p class='mb-0'><strong>3. Platné topologické uspořádání (Kahnův algoritmus):</strong> "
        f"<span class='badge bg-success fs-6'>{order_str}</span></p>"
    )

    return {
        "scenario_type": "toposort",
        "title": "Harmonogram vývojového projektu (Topologické uspořádání)",
        "algorithm_badge": "Topologické řazení (DAG)",
        "story": story,
        "questions": questions,
        "student_table_html": student_table_html,
        "teacher_solution": teacher_solution,
        "target_nodes": f"{len(nodes_sorted)} činností",
        "solution_summary": f"Harmonogram: {order_str}"
    }


def _scenario_max_flow(G: nx.DiGraph, graph_data: dict, start_node: int, end_node: int) -> dict:
    s_lbl = node_to_letter(start_node)
    t_lbl = node_to_letter(end_node)

    sol = ford_fulkerson_max_flow(G, start_node, end_node)
    max_flow = sol.get("max_flow", 0)
    cut_edges = sol.get("min_cut_edges") or []
    cut_partition = sol.get("min_cut_partition") or [[], []]
    flow_edges = sol.get("flow_edges") or []

    cut_edge_strs = [
        f"{node_to_letter(e['source'])} → {node_to_letter(e['target'])} (kapacita {e.get('capacity', 0)})"
        for e in cut_edges
    ]
    part_s_lbls = [node_to_letter(n) for n in sorted(cut_partition[0])] if len(cut_partition) >= 1 else []
    part_t_lbls = [node_to_letter(n) for n in sorted(cut_partition[1])] if len(cut_partition) >= 2 else []

    active_flows = [
        f"{node_to_letter(e['source'])}→{node_to_letter(e['target'])}: <strong>{e['flow']}/{e['capacity']}</strong>"
        for e in flow_edges
        if e.get("flow", 0) > 0
    ]

    story = (
        f"Produktovodní síť spojuje terminál v přístavu <strong>{s_lbl} ({start_node})</strong> (zdroj <em>s</em>) "
        f"s centrálním zásobníkem <strong>{t_lbl} ({end_node})</strong> (stok <em>t</em>). Čísla na orientovaných hranách "
        f"udávají maximální hodinovou kapacitu potrubí v m³/hod."
    )
    questions = [
        f"Pomocí <strong>Fordova-Fulkersonova (Edmondsova-Karpova) algoritmu</strong> určete maximální průtok sítí ze zdroje <strong>{s_lbl}</strong> do stoku <strong>{t_lbl}</strong>.",
        "Postupně zapisujte nalezené zlepšující (augmentační) cesty a jejich úzká hrdla (reziduální kapacity).",
        "Uveďte rozdělení vrcholů na množiny <code>(S, T)</code> minimálního řezu a vypište hrany minimálního řezu.",
        "Ověřte platnost <em>Věty o maximálním toku a minimálním řezu</em> porovnáním součtu kapacit hran řezu s velikostí toku."
    ]

    student_table_html = (
        "<div class='small fw-bold text-muted text-uppercase mb-1'>Tabulka nalezených zlepšujících (augmentačních) cest:</div>"
        "<table class='table table-bordered table-sm mb-3'>"
        "<thead class='table-light'><tr><th style='width:55px;'>Krok</th><th>Zlepšující cesta ze zdroje do stoku</th><th style='width:180px;'>Přírůstek toku (Δf)</th></tr></thead>"
        "<tbody>"
        "<tr><td class='text-center'>1.</td><td>&nbsp;</td><td>&nbsp;</td></tr>"
        "<tr><td class='text-center'>2.</td><td>&nbsp;</td><td>&nbsp;</td></tr>"
        "<tr><td class='text-center'>3.</td><td>&nbsp;</td><td>&nbsp;</td></tr>"
        "<tr><td colspan='2' class='text-end fw-bold'>Celkový maximální tok |f_max| =</td><td>&nbsp;</td></tr>"
        "</tbody></table>"
    )

    teacher_solution = (
        f"<p class='mb-1'><strong>1. Maximální tok sítí |f<sub>max</sub>|:</strong> <span class='badge bg-success fs-6'>{max_flow} m³/hod</span></p>"
        f"<p class='mb-1'><strong>2. Minimální s–t řez:</strong> Množina S = {{{', '.join(part_s_lbls)}}}, Množina T = {{{', '.join(part_t_lbls)}}}</p>"
        f"<p class='mb-1'><strong>3. Hrany minimálního řezu (úzké hrdlo sítě):</strong> {', '.join(cut_edge_strs) if cut_edge_strs else 'Žádná průchozí hrana'}</p>"
        f"<p class='mb-0'><strong>4. Rozložení toku na nasycených a aktivních hranách (tok/kapacita):</strong><br>"
        f"{', '.join(active_flows) if active_flows else 'Nulový tok'}</p>"
    )

    return {
        "scenario_type": "max_flow",
        "title": f"Přepravní kapacita potrubní sítě ({s_lbl} → {t_lbl})",
        "algorithm_badge": "Ford-Fulkerson (Max-Flow & Min-Cut)",
        "story": story,
        "questions": questions,
        "student_table_html": student_table_html,
        "teacher_solution": teacher_solution,
        "target_nodes": f"{s_lbl} → {t_lbl}",
        "solution_summary": f"Max tok: {max_flow}, Řez: {', '.join(cut_edge_strs) if cut_edge_strs else '—'}"
    }
