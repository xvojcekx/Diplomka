"""
exporter.py — Export výsledků pro UIS MENDELU

Exportuje vygenerovaná grafová zadání do CSV a JSON formátů
pro import do testovacího prostředí UIS.
"""

import csv
import json
import io
from typing import List


def index_to_label(i: int) -> str:
    """Převede číselný index uzlu (0, 1, 2...) na písmenný label (A, B, C... Z, AA, AB...)."""
    if i < 26:
        return chr(65 + i)
    return chr(65 + (i // 26) - 1) + chr(65 + (i % 26))


def export_to_tg(graph_data: dict, use_letters: bool = True) -> str:
    """
    Exportuje jeden graf do formátu .tg (pro UIS MENDELU).
    
    Příklad výstupu (vážený):
    u A;
    u B;
    h A > B 10 :h1;
    
    Příklad výstupu (nevážený):
    h A > B :h1;
    """
    output = io.StringIO()
    edges = graph_data.get("edge_list", [])
    config = graph_data.get("config", {})
    is_weighted = config.get("weighted", False)
    
    node_count = graph_data.get("properties", {}).get("node_count", 0)
    
    def fmt_node(n: int) -> str:
        return index_to_label(int(n)) if use_letters else str(n)

    # Uzly
    for i in range(node_count):
        output.write(f"u {fmt_node(i)};\n")
        
    # Hrany
    for idx, edge in enumerate(edges):
        source = fmt_node(edge["source"])
        target = fmt_node(edge["target"])
        weight = edge.get("weight")
        
        op = ">"
        
        if is_weighted and weight is not None:
            w_val = int(weight) if isinstance(weight, float) and weight.is_integer() else weight
            output.write(f"h {source} {op} {target} {w_val} :h{idx+1};\n")
        else:
            output.write(f"h {source} {op} {target} :h{idx+1};\n")
            
    return output.getvalue()


def parse_tg(tg_content: str, directed: bool = False) -> dict:
    """
    Načte graf ze zápisu ve formátu .tg a převede jej na strukturu kompatibilní s aplikací.

    Podporuje:
        u A;
        h A > B 2 :h1;
        h A < B 3 :h2;
        h A - B :h3;
    """
    import networkx as nx

    raw_nodes = []
    raw_edges = []
    has_weights = False

    statements = tg_content.replace("\r", "\n").split(";")
    for stmt in statements:
        line = stmt.strip()
        if not line:
            continue
        parts = line.split()
        if not parts:
            continue

        kind = parts[0].lower()
        if kind == "u" and len(parts) >= 2:
            node_name = parts[1]
            if node_name not in raw_nodes:
                raw_nodes.append(node_name)
        elif kind == "h" and len(parts) >= 4:
            u_name = parts[1]
            op = parts[2]
            v_name = parts[3]
            if u_name not in raw_nodes:
                raw_nodes.append(u_name)
            if v_name not in raw_nodes:
                raw_nodes.append(v_name)

            weight = None
            for token in parts[4:]:
                if not token.startswith(":"):
                    try:
                        val = float(token)
                        weight = int(val) if val.is_integer() else val
                        has_weights = True
                    except ValueError:
                        pass

            if op == "<":
                u_name, v_name = v_name, u_name

            raw_edges.append((u_name, v_name, weight))

    if len(raw_nodes) < 2:
        raise ValueError("Soubor .tg musí obsahovat alespoň 2 uzly (např. 'u A; u B;').")
    if len(raw_edges) < 1:
        raise ValueError("Soubor .tg musí obsahovat alespoň 1 hranu (např. 'h A > B :h1;').")

    node_map = {name: idx for idx, name in enumerate(raw_nodes)}
    n = len(raw_nodes)
    G = nx.DiGraph() if directed else nx.Graph()
    G.add_nodes_from(range(n))

    edge_list = []
    for u_name, v_name, weight in raw_edges:
        u_idx = node_map[u_name]
        v_idx = node_map[v_name]
        w = weight if (has_weights and weight is not None) else (1 if has_weights else None)
        if w is not None:
            G.add_edge(u_idx, v_idx, weight=w)
            edge_list.append({"source": u_idx, "target": v_idx, "weight": w})
        else:
            G.add_edge(u_idx, v_idx)
            edge_list.append({"source": u_idx, "target": v_idx})

    matrix = [[0.0] * n for _ in range(n)]
    for u, v, data in G.edges(data=True):
        w = data.get("weight", 1) if has_weights else 1
        matrix[u][v] = w
        if not directed:
            matrix[v][u] = w

    return {
        "graph": G,
        "adjacency_matrix": matrix,
        "edge_list": edge_list,
        "weighted": has_weights,
        "directed": directed,
        "node_count": n,
        "edge_count": G.number_of_edges(),
    }



def export_to_csv(graphs: list) -> str:
    """
    CSV formát pro UIS MENDELU.

    Sloupce: graph_id, description, question_type, correct_answer

    Args:
        graphs: seznam grafových výsledků z graphs_store

    Returns:
        str: CSV obsah jako string
    """
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_ALL)

    # Hlavička
    writer.writerow([
        "graph_id",
        "popis_grafu",
        "typ_otazky",
        "otazka",
        "spravna_odpoved"
    ])

    for graph_data in graphs:
        graph_id = graph_data["graph_id"]
        props = graph_data.get("properties", {})
        algos = graph_data.get("algorithms", {})
        config = graph_data.get("config", {})

        # Popis grafu
        desc_parts = []
        desc_parts.append(f"Uzlů: {props.get('node_count', '?')}")
        desc_parts.append(f"Hran: {props.get('edge_count', '?')}")
        if config.get("directed"):
            desc_parts.append("orientovaný")
        if config.get("weighted"):
            desc_parts.append("ohodnocený")
        if config.get("connected"):
            desc_parts.append("souvislý")
        description = ", ".join(desc_parts)

        # Nejkratší cesta
        if "shortest_path" in algos:
            sp = algos["shortest_path"]
            if sp.get("error") is None:
                writer.writerow([
                    graph_id,
                    description,
                    "shortest_path",
                    f"Jaká je nejkratší cesta z {sp['path'][0]} do {sp['path'][-1]}?",
                    f"Cesta: {' → '.join(map(str, sp['path']))}, Vzdálenost: {sp['distance']}"
                ])

        # MST
        if "mst" in algos:
            mst = algos["mst"]
            if mst.get("error") is None:
                writer.writerow([
                    graph_id,
                    description,
                    "mst_weight",
                    "Jaká je celková váha minimální kostry (MST)?",
                    f"Celková váha: {mst['total_weight']}"
                ])

        # Topologické třídění
        if "topological_sort" in algos:
            ts = algos["topological_sort"]
            if ts.get("error") is None and ts.get("valid"):
                writer.writerow([
                    graph_id,
                    description,
                    "topological_order",
                    "Jaké je topologické pořadí uzlů?",
                    f"Pořadí: {' → '.join(map(str, ts['order']))}"
                ])

        # Bipartitnost
        if "bipartite" in algos:
            bp = algos["bipartite"]
            if bp.get("error") is None:
                writer.writerow([
                    graph_id,
                    description,
                    "bipartite_check",
                    "Je graf bipartitní? Pokud ano, uveďte rozdělení.",
                    f"Bipartitní: {'Ano' if bp['is_bipartite'] else 'Ne'}"
                    + (f", Množiny: {bp['sets']}" if bp.get("sets") else "")
                ])

        # Bellman-Ford
        if "bellman_ford" in algos:
            bf = algos["bellman_ford"]
            if bf.get("error") is None and bf.get("path"):
                writer.writerow([
                    graph_id,
                    description,
                    "bellman_ford",
                    f"Jaká je nejkratší cesta (Bellman-Ford) z u{bf['source']} do u{bf['target']}?",
                    f"Cesta: {' → '.join(map(str, bf['path']))}, Vzdálenost: {bf['distance']}"
                ])

        # Maximální tok a minimální řez
        if "max_flow" in algos:
            mf = algos["max_flow"]
            if mf.get("error") is None:
                writer.writerow([
                    graph_id,
                    description,
                    "max_flow",
                    f"Jaká je velikost maximálního toku (a minimálního řezu) z u{mf.get('source', 0)} do u{mf.get('sink', '?')}?",
                    f"Maximální tok: {mf['max_flow']}"
                ])

        # Barvení grafu
        if "coloring" in algos:
            col = algos["coloring"]
            if col.get("error") is None:
                writer.writerow([
                    graph_id,
                    description,
                    "graph_coloring",
                    "Jaký je horní odhad chromatického čísla (počet barev při greedy barvení)?",
                    f"Počet barev: {col['chromatic_number']}, Obarvení: {col['coloring']}"
                ])

        # Eulerovský tah / kružnice
        if "euler" in algos:
            eu = algos["euler"]
            if eu.get("error") is None:
                writer.writerow([
                    graph_id,
                    description,
                    "euler_check",
                    "Obsahuje graf Eulerovský tah nebo Eulerovskou kružnici?",
                    f"Kružnice: {'Ano' if eu['has_euler_circuit'] else 'Ne'}, Tah: {'Ano' if eu['has_euler_path'] else 'Ne'}"
                ])

        # Hamiltonovská cesta / kružnice
        if "hamilton" in algos:
            hm = algos["hamilton"]
            if hm.get("error") is None:
                writer.writerow([
                    graph_id,
                    description,
                    "hamilton_check",
                    "Obsahuje graf Hamiltonovskou cestu nebo kružnici?",
                    f"Kružnice: {'Ano' if hm['has_hamilton_cycle'] else 'Ne'}, Cesta: {'Ano' if hm['has_hamilton_path'] else 'Ne'}"
                ])

        # Vlastnosti grafu
        writer.writerow([
            graph_id,
            description,
            "graph_properties",
            "Uveďte základní vlastnosti grafu (hustota, průměr, stupňová posloupnost).",
            f"Hustota: {props.get('density', '?')}, "
            f"Průměr: {props.get('diameter', '?')}, "
            f"Stupně: {props.get('degree_sequence', '?')}"
        ])

    return output.getvalue()


def export_to_json(graphs: list) -> str:
    """
    JSON formát pro případný přímý import do UIS.

    Args:
        graphs: seznam grafových výsledků z graphs_store

    Returns:
        str: JSON string
    """
    export_data = []

    for graph_data in graphs:
        item = {
            "graph_id": graph_data["graph_id"],
            "config": graph_data.get("config", {}),
            "properties": graph_data.get("properties", {}),
            "algorithms": {},
            "adjacency_matrix": graph_data.get("adjacency_matrix", []),
            "edge_list": graph_data.get("edge_list", []),
        }

        # Přidej výsledky algoritmů (bez chyb)
        algos = graph_data.get("algorithms", {})
        for key, value in algos.items():
            if isinstance(value, dict) and value.get("error") is None:
                item["algorithms"][key] = value

        export_data.append(item)

    return json.dumps(export_data, indent=2, ensure_ascii=False, default=str)
