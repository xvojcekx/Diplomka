"""
grader.py — Automatický validátor studentských řešení (Grader v2)

Ověřuje správnost studentských odpovědí i pro víceznačné grafové úlohy,
kde může existovat více různých správných řešení (např. různá topologická
uspořádání, různé minimální kostry se stejnou vahou, alternativní nejkratší
cesty stejné délky nebo různé Eulerovské tahy).

Pokud má odpověď neočekávaný formát, nastaví příznak `manual_review: True`
pro upozornění vyučujícího.
"""

import re
import networkx as nx


def _parse_node_token(token: str, n_nodes: int) -> int:
    """
    Převede textové označení uzlu ('0', 'u0', 'U0', 'A', 'B'...) na číselný index 0..n-1.
    Vyvolá ValueError, pokud token nelze interpretovat nebo je mimo rozsah.
    """
    t = token.strip().strip(",;()[]{}")
    if not t:
        raise ValueError("Prázdný identifikátor uzlu.")

    # Tvar u0, u1, v2...
    if len(t) >= 2 and t[0].lower() in ("u", "v") and t[1:].isdigit():
        idx = int(t[1:])
        if 0 <= idx < n_nodes:
            return idx
        raise ValueError(f"Uzel '{t}' je mimo rozsah grafu (0..{n_nodes - 1}).")

    # Číselný tvar 0, 1, 2...
    if t.isdigit():
        idx = int(t)
        if 0 <= idx < n_nodes:
            return idx
        raise ValueError(f"Uzel '{t}' je mimo rozsah grafu (0..{n_nodes - 1}).")

    # Písmenný tvar A, B, C... Z, AA...
    if t.isalpha() and len(t) <= 2:
        t_up = t.upper()
        if len(t_up) == 1:
            idx = ord(t_up) - 65
        else:
            idx = (ord(t_up[0]) - 64) * 26 + (ord(t_up[1]) - 65)
        if 0 <= idx < n_nodes:
            return idx
        raise ValueError(f"Uzel '{t}' (index {idx}) v grafu neexistuje.")

    raise ValueError(f"Nerozpoznaný formát uzlu: '{t}'. Použijte např. u0, 0 nebo A.")


def _parse_node_sequence(answer: str, n_nodes: int) -> list:
    """Rozparsuje posloupnost uzlů oddělených čárkou, mezerou nebo šipkou (→, ->, >)."""
    cleaned = answer.replace("->", " ").replace("→", " ").replace(">", " ").replace(",", " ").replace(";", " ")
    tokens = [tok for tok in cleaned.split() if tok.strip()]
    if not tokens:
        raise ValueError("Nebyla zadána žádná posloupnost uzlů.")
    return [_parse_node_token(tok, n_nodes) for tok in tokens]


def _parse_edge_list_answer(answer: str, edge_list: list, n_nodes: int, directed: bool = False) -> list:
    """
    Rozparsuje seznam hran zadaný studentem.
    Podporuje zápis:
    - pomocí označení hran: 'h1, h3, h5'
    - pomocí dvojic uzlů: 'u0-u1, u1-u2' nebo 'A-B, B-C' nebo '0 1, 1 2'
    Vrací seznam dvojic (u, v).
    """
    raw_items = [item.strip() for item in re.split(r"[,;\n]+", answer) if item.strip()]
    if not raw_items:
        raise ValueError("Nebyla zadána žádná hrana.")

    # Pokud je v jedné položce více identifikátorů h1 h2 h3 oddělených mezerou
    expanded_items = []
    for item in raw_items:
        if all(re.match(r"^[hH]\d+$", tok) for tok in item.split()):
            expanded_items.extend(item.split())
        else:
            expanded_items.append(item)

    parsed_edges = []
    for item in expanded_items:
        # Tvar h1, h2...
        m_h = re.match(r"^[hH](\d+)$", item.strip())
        if m_h:
            h_idx = int(m_h.group(1)) - 1
            if 0 <= h_idx < len(edge_list):
                e = edge_list[h_idx]
                parsed_edges.append((int(e["source"]), int(e["target"])))
                continue
            else:
                raise ValueError(f"Hrana h{h_idx + 1} v grafu neexistuje (graf má {len(edge_list)} hran).")

        # Tvar u0-u1, A->B, 0:1 apod.
        parts = [p for p in re.split(r"\s*(?:->|→|–|-|>|:|\s)\s*", item.strip()) if p]
        if len(parts) == 2:
            u = _parse_node_token(parts[0], n_nodes)
            v = _parse_node_token(parts[1], n_nodes)
            parsed_edges.append((u, v))
        else:
            raise ValueError(f"Nelze rozpoznat hranu '{item}'. Použijte např. 'h1, h2' nebo 'u0-u1, u1-u2'.")

    return parsed_edges


def validate_mst(G: nx.Graph, edge_list: list, student_answer: str) -> dict:
    """
    Ověří, zda studentem zadaná množina hran tvoří platnou minimální kostru (MST).
    Uzná libovolnou kostru, která je souvislá, acyklická a má minimální možnou váhu.
    """
    if G.is_directed():
        return {
            "passed": False,
            "score": 0,
            "manual_review": False,
            "feedback": "Minimální kostra (MST) je definována pouze pro neorientované grafy.",
        }
    if not nx.is_connected(G):
        return {
            "passed": False,
            "score": 0,
            "manual_review": False,
            "feedback": "Graf není souvislý — minimální kostra neexistuje.",
        }

    n = G.number_of_nodes()
    ref_mst = nx.minimum_spanning_tree(G, algorithm="kruskal")
    ref_weight = sum(d.get("weight", 1) for _, _, d in ref_mst.edges(data=True))

    # Pokud student zadal pouze jedno číslo (celkovou váhu kostry)
    stripped = student_answer.strip()
    try:
        only_weight = float(stripped.replace(",", "."))
        if abs(only_weight - ref_weight) < 1e-6:
            return {
                "passed": True,
                "score": 100,
                "manual_review": False,
                "feedback": f"Správně! Celková váha minimální kostry je {ref_weight}.",
                "reference_weight": ref_weight,
            }
        else:
            return {
                "passed": False,
                "score": 0,
                "manual_review": False,
                "feedback": f"Nesprávná váha kostry: zadáno {only_weight}, ale minimální kostra má váhu {ref_weight}.",
                "reference_weight": ref_weight,
            }
    except ValueError:
        pass

    try:
        student_edges = _parse_edge_list_answer(student_answer, edge_list, n, directed=False)
    except ValueError as e:
        return {
            "passed": False,
            "score": 0,
            "manual_review": True,
            "feedback": f"[NUTNÁ KONTROLA FORMÁTU] {str(e)}",
        }

    # Zkontroluj existenci všech hran v původním grafu
    subG = nx.Graph()
    subG.add_nodes_from(G.nodes())
    student_weight = 0.0

    for u, v in student_edges:
        if not G.has_edge(u, v):
            return {
                "passed": False,
                "score": 0,
                "manual_review": False,
                "feedback": f"Hrana u{u}–u{v} v zadaném grafu vůbec neexistuje.",
            }
        if subG.has_edge(u, v):
            return {
                "passed": False,
                "score": 0,
                "manual_review": False,
                "feedback": f"Hrana u{u}–u{v} je v odpovědi uvedena duplicitně.",
            }
        w = G[u][v].get("weight", 1)
        subG.add_edge(u, v, weight=w)
        student_weight += w

    if len(student_edges) != n - 1:
        return {
            "passed": False,
            "score": 25 if nx.is_forest(subG) else 0,
            "manual_review": False,
            "feedback": f"Kostra grafu s {n} uzly musí obsahovat přesně {n - 1} hran, ale zadáno {len(student_edges)} hran.",
        }

    if not nx.is_connected(subG):
        return {
            "passed": False,
            "score": 25,
            "manual_review": False,
            "feedback": "Zadané hrany netvoří souvislou kostru (obsahují cyklus a některé uzly nejsou propojeny).",
        }

    if abs(student_weight - ref_weight) > 1e-6:
        return {
            "passed": False,
            "score": 50,
            "manual_review": False,
            "feedback": (
                f"Zadané hrany sice tvoří platnou kostru grafu, ale její váha ({student_weight}) "
                f"není minimální. Minimální kostra má váhu {ref_weight}."
            ),
            "student_weight": student_weight,
            "reference_weight": ref_weight,
        }

    return {
        "passed": True,
        "score": 100,
        "manual_review": False,
        "feedback": f"Výborně! Zadané hrany tvoří platnou minimální kostru s optimální vahou {ref_weight}.",
        "student_weight": student_weight,
        "reference_weight": ref_weight,
    }


def validate_shortest_path(G: nx.Graph, source: int, target: int, student_answer: str) -> dict:
    """
    Ověří, zda studentem zadaná posloupnost uzlů (nebo délka) představuje platnou
    nejkratší cestu ze source do target. Uzná libovolnou nejkratší cestu se stejnou
    minimální délkou.
    """
    weight_attr = "weight" if nx.is_weighted(G) else None
    if not nx.has_path(G, source, target):
        return {
            "passed": False,
            "score": 0,
            "manual_review": False,
            "feedback": f"V grafu neexistuje žádná cesta z u{source} do u{target}.",
        }

    try:
        ref_dist = nx.bellman_ford_path_length(G, source=source, target=target, weight=weight_attr)
        ref_path = nx.bellman_ford_path(G, source=source, target=target, weight=weight_attr)
    except nx.NetworkXUnbounded:
        return {
            "passed": False,
            "score": 0,
            "manual_review": False,
            "feedback": "Graf obsahuje záporný cyklus — nejkratší cesta není definována.",
        }

    # Pokud student zadal pouze číselnou vzdálenost
    stripped = student_answer.strip()
    try:
        only_dist = float(stripped.replace(",", "."))
        if abs(only_dist - ref_dist) < 1e-6:
            return {
                "passed": True,
                "score": 100,
                "manual_review": False,
                "feedback": f"Správně! Délka nejkratší cesty z u{source} do u{target} je {ref_dist}.",
            }
        else:
            return {
                "passed": False,
                "score": 0,
                "manual_review": False,
                "feedback": f"Nesprávná délka cesty: zadáno {only_dist}, ale nejkratší cesta má délku {ref_dist}.",
            }
    except ValueError:
        pass

    n = G.number_of_nodes()
    try:
        path_nodes = _parse_node_sequence(student_answer, n)
    except ValueError as e:
        return {
            "passed": False,
            "score": 0,
            "manual_review": True,
            "feedback": f"[NUTNÁ KONTROLA FORMÁTU] {str(e)}",
        }

    if path_nodes[0] != source or path_nodes[-1] != target:
        return {
            "passed": False,
            "score": 0,
            "manual_review": False,
            "feedback": f"Cesta musí začínat v uzlu u{source} a končit v uzlu u{target} (zadáno u{path_nodes[0]} → … → u{path_nodes[-1]}).",
        }

    student_dist = 0.0
    for i in range(len(path_nodes) - 1):
        u, v = path_nodes[i], path_nodes[i + 1]
        if not G.has_edge(u, v):
            return {
                "passed": False,
                "score": 0,
                "manual_review": False,
                "feedback": f"Přechod u{u} → u{v} v grafu neexistuje.",
            }
        student_dist += G[u][v].get("weight", 1) if nx.is_weighted(G) else 1

    if abs(student_dist - ref_dist) > 1e-6:
        return {
            "passed": False,
            "score": 50,
            "manual_review": False,
            "feedback": (
                f"Zadaná posloupnost je platná cesta z u{source} do u{target}, ale má délku {student_dist}. "
                f"Nejkratší možná cesta má délku {ref_dist} (např. {' → '.join(f'u{x}' for x in ref_path)})."
            ),
        }

    return {
        "passed": True,
        "score": 100,
        "manual_review": False,
        "feedback": f"Výborně! Cesta {' → '.join(f'u{x}' for x in path_nodes)} je platná nejkratší cesta s minimální délkou {ref_dist}.",
    }


def validate_topological_sort(G: nx.Graph, student_answer: str) -> dict:
    """
    Ověří, zda studentem zadané pořadí uzlů je platným topologickým uspořádáním DAGu.
    Uzná libovolné platné topologické pořadí (nejen jedno referenční).
    """
    if not G.is_directed():
        return {
            "passed": False,
            "score": 0,
            "manual_review": False,
            "feedback": "Topologické třídění je definováno pouze pro orientované grafy.",
        }
    if not nx.is_directed_acyclic_graph(G):
        return {
            "passed": False,
            "score": 0,
            "manual_review": False,
            "feedback": "Graf obsahuje orientovaný cyklus — topologické uspořádání neexistuje.",
        }

    n = G.number_of_nodes()
    try:
        order = _parse_node_sequence(student_answer, n)
    except ValueError as e:
        return {
            "passed": False,
            "score": 0,
            "manual_review": True,
            "feedback": f"[NUTNÁ KONTROLA FORMÁTU] {str(e)}",
        }

    if len(order) != n or set(order) != set(G.nodes()):
        return {
            "passed": False,
            "score": 0,
            "manual_review": False,
            "feedback": f"Topologické uspořádání musí obsahovat všech {n} uzlů právě jednou (zadáno {len(order)} uzlů).",
        }

    pos = {node: idx for idx, node in enumerate(order)}
    violated = []
    for u, v in G.edges():
        if pos[u] >= pos[v]:
            violated.append(f"u{u}→u{v}")

    if violated:
        return {
            "passed": False,
            "score": 0,
            "manual_review": False,
            "feedback": f"Pořadí porušuje orientaci hran: {', '.join(violated[:5])} (zdrojový uzel musí být před cílovým).",
        }

    return {
        "passed": True,
        "score": 100,
        "manual_review": False,
        "feedback": f"Výborně! Pořadí {' → '.join(f'u{x}' for x in order)} je platné topologické uspořádání.",
    }


def validate_student_answer(
    G: nx.Graph,
    edge_list: list,
    task_type: str,
    student_answer: str,
    source: int = 0,
    target: int = None,
) -> dict:
    """
    Hlavní rozcestník validátoru studentských odpovědí.

    Podporované task_type:
    - 'mst': Minimální kostra (seznam hran nebo celková váha)
    - 'shortest_path': Nejkratší cesta (posloupnost uzlů nebo vzdálenost)
    - 'topological_sort': Topologické uspořádání (posloupnost uzlů)
    """
    nodes = sorted(G.nodes())
    if target is None and nodes:
        target = nodes[-1]

    if not student_answer or not student_answer.strip():
        return {
            "passed": False,
            "score": 0,
            "manual_review": False,
            "feedback": "Odpověď je prázdná.",
        }

    if task_type == "mst":
        return validate_mst(G, edge_list, student_answer)
    elif task_type == "shortest_path":
        return validate_shortest_path(G, int(source), int(target), student_answer)
    elif task_type == "topological_sort":
        return validate_topological_sort(G, student_answer)
    else:
        return {
            "passed": False,
            "score": 0,
            "manual_review": True,
            "feedback": f"Neznámý typ úlohy k validaci: {task_type}",
        }
