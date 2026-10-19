"""
main.py — FastAPI aplikace pro generování a kontrolu grafů

Routy, vizualizace (Matplotlib + Pyvis), in-memory stav.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import uuid
import random
import base64
import matplotlib
from datetime import datetime
matplotlib.use("Agg")  # Server nemá display
import matplotlib.pyplot as plt
import networkx as nx
from pyvis.network import Network

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from models import GraphConfig, BatchConfig
from generator import generate_graph
from solver import (
    shortest_path_dijkstra,
    minimum_spanning_tree,
    topological_sort,
    is_bipartite_check,
    graph_properties,
    kruskal_steps,
    boruvka_steps,
    dijkstra_steps,
    bfs_steps,
    dfs_steps,
)
from exporter import export_to_csv, export_to_json, export_to_tg, parse_tg
from database import (
    init_db, save_graph, get_graph, get_all_graphs,
    delete_graph, delete_all_graphs, count_graphs, save_positions, load_positions
)

import io

# ============================================================================
# APP SETUP
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializace SQLite databáze při startu aplikace."""
    init_db()
    yield


app = FastAPI(title="Teorie Grafů — Generátor zadání", version="1.0.0", lifespan=lifespan)

# Adresáře
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
GRAPHS_DIR = os.path.join(STATIC_DIR, "graphs")

# Vytvoř složku pro grafy
os.makedirs(GRAPHS_DIR, exist_ok=True)

# Statické soubory a šablony
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


def _cleanup_graph_files(graph_id: str) -> None:
    """Odstraní statické soubory (.png, .html) smazaného grafu."""
    for ext in ("png", "html"):
        filepath = os.path.join(GRAPHS_DIR, f"{graph_id}.{ext}")
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except OSError:
                pass



def _reconstruct_graph(graph_data: dict) -> nx.Graph:
    """
    Rekonstruuje NetworkX graf z uložených dat (hrany + konfigurace).
    Volá se pouze tehdy, když je potřeba spustit algoritmy
    (vizualizace průchodu, API graf data).
    """
    config = graph_data.get("config", {})
    is_directed = config.get("directed", False)
    G = nx.DiGraph() if is_directed else nx.Graph()

    # Přidej uzly (z matice sousednosti — zachovává počet uzlů)
    matrix = graph_data.get("adjacency_matrix", [])
    for i in range(len(matrix)):
        G.add_node(i)

    # Přidej hrany
    for edge in graph_data.get("edge_list", []):
        if edge.get("weight") is not None:
            G.add_edge(edge["source"], edge["target"], weight=edge["weight"])
        else:
            G.add_edge(edge["source"], edge["target"])

    return G


# ============================================================================
# VIZUALIZACE
# ============================================================================

def render_graph_png(G: nx.Graph, graph_id: str) -> str:
    """Vyrenderuje graf jako PNG do /static/graphs/{id}.png"""
    fig, ax = plt.subplots(1, 1, figsize=(10, 8))

    seed = 42
    pos = nx.spring_layout(G, seed=seed, k=2.0)

    # Barvy uzlů
    node_colors = ["#6366f1"] * G.number_of_nodes()

    # Nakresli uzly
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colors,
                           node_size=600, edgecolors="#4338ca", linewidths=2)

    # Nakresli hrany
    edge_color = "#94a3b8"
    if G.is_directed():
        nx.draw_networkx_edges(G, pos, ax=ax, edge_color=edge_color,
                               arrows=True, arrowsize=20, width=2,
                               connectionstyle="arc3,rad=0.1")
    else:
        nx.draw_networkx_edges(G, pos, ax=ax, edge_color=edge_color, width=2)

    # Popisky uzlů
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=12, font_weight="bold",
                            font_color="white")

    # Váhy na hranách
    if nx.is_weighted(G):
        edge_labels = nx.get_edge_attributes(G, "weight")
        nx.draw_networkx_edge_labels(G, pos, edge_labels, ax=ax,
                                     font_size=10, font_color="#dc2626",
                                     bbox=dict(boxstyle="round,pad=0.2",
                                              facecolor="white", alpha=0.8))

    ax.set_title(f"Graf {graph_id[:8]}", fontsize=14, fontweight="bold")
    ax.axis("off")
    fig.tight_layout()

    # Uloží PNG
    filepath = os.path.join(GRAPHS_DIR, f"{graph_id}.png")
    fig.savefig(filepath, dpi=150, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)

    return f"/static/graphs/{graph_id}.png"


def render_graph_interactive(G: nx.Graph, graph_id: str) -> str:
    """Vyrenderuje interaktivní HTML pomocí Pyvis do /static/graphs/{id}.html"""
    net = Network(
        height="600px",
        width="100%",
        directed=G.is_directed(),
        bgcolor="#1e1e2e",
        font_color="white",
    )

    # Přidej uzly
    for node in G.nodes():
        net.add_node(
            int(node),
            label=str(node),
            color="#6366f1",
            size=25,
            font={"size": 16, "color": "white"},
        )

    # Přidej hrany
    for u, v, data in G.edges(data=True):
        weight = data.get("weight", None)
        if weight is not None:
            net.add_edge(int(u), int(v), value=weight,
                        title=f"Váha: {weight}", label=str(weight),
                        font={"size": 12, "color": "#ef4444"})
        else:
            net.add_edge(int(u), int(v))

    # Pyvis options
    net.set_options("""
    {
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -50,
          "centralGravity": 0.01,
          "springLength": 150,
          "springConstant": 0.08
        },
        "solver": "forceAtlas2Based",
        "stabilization": {"iterations": 150}
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 200,
        "navigationButtons": true
      }
    }
    """)

    filepath = os.path.join(GRAPHS_DIR, f"{graph_id}.html")
    net.save_graph(filepath)

    return f"/static/graphs/{graph_id}.html"


# ============================================================================
# ROUTY
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Úvodní stránka."""
    return templates.TemplateResponse(request, "index.html", {
        "total_graphs": count_graphs(),
    })


@app.get("/generate", response_class=HTMLResponse)
async def generate_form(request: Request):
    """Formulář pro konfiguraci generování."""
    return templates.TemplateResponse(request, "generate.html", {})


@app.post("/generate")
async def generate_post(
    request: Request,
    batch_size: int = Form(1),
    node_min: int = Form(5),
    node_max: int = Form(10),
    edge_min: int = Form(6),
    edge_max: int = Form(15),
    directed: bool = Form(False),
    weighted: bool = Form(True),
    weight_min: int = Form(1),
    weight_max: int = Form(10),
    connected: bool = Form(True),
    acyclic: bool = Form(False),
    bipartite: bool = Form(False),
    seed: str = Form(""),
    algo_shortest_path: bool = Form(False),
    algo_mst: bool = Form(False),
    algo_topological: bool = Form(False),
    algo_bipartite: bool = Form(False),
):
    """Zpracuje formulář, vygeneruje grafy."""
    base_seed = int(seed) if seed.strip() else None
    generated_ids = []
    errors = []

    for i in range(batch_size):
        rng = random.Random(base_seed + i if base_seed is not None else None)
        n = rng.randint(node_min, node_max)
        m = rng.randint(edge_min, edge_max)

        # Automatické úpravy k zabránění chybám při nesmyslných vstupech
        if acyclic and not directed:
            m = n - 1
            
        if connected and not directed:
            m = max(m, n - 1)

        max_e = n * (n - 1) if directed else n * (n - 1) // 2
        if acyclic and directed:
            max_e = n * (n - 1) // 2
            
        if bipartite:
            half_a = n // 2
            half_b = n - half_a
            max_bipartite = half_a * half_b
            if directed:
                max_e = min(max_e, 2 * max_bipartite)
            else:
                max_e = min(max_e, max_bipartite)
                
        m = min(m, max_e)

        config = GraphConfig(
            node_count=n,
            edge_count=m,
            directed=directed,
            weighted=weighted,
            weight_min=weight_min,
            weight_max=weight_max,
            connected=connected,
            acyclic=acyclic,
            bipartite=bipartite,
            seed=base_seed + i if base_seed is not None else None,
        )

        try:
            result = generate_graph(config)
            G = result["graph"]
            graph_id = str(uuid.uuid4())

            # Vizualizace
            png_path = render_graph_png(G, graph_id)
            interactive_path = render_graph_interactive(G, graph_id)

            # Vlastnosti
            props = graph_properties(G)

            # Algoritmy
            algos = {}

            if algo_shortest_path and G.number_of_nodes() >= 2:
                nodes = sorted(G.nodes())
                source, target = nodes[0], nodes[-1]
                algos["shortest_path"] = shortest_path_dijkstra(G, source, target)

            if algo_mst and not directed:
                algos["mst"] = minimum_spanning_tree(G)

            if algo_topological and directed:
                algos["topological_sort"] = topological_sort(G)

            if algo_bipartite:
                algos["bipartite"] = is_bipartite_check(G)

            # Ulož do SQLite databáze
            graph_record = {
                "graph_id": graph_id,
                "config": config.model_dump(),
                "properties": props,
                "algorithms": algos,
                "adjacency_matrix": result["adjacency_matrix"],
                "edge_list": result["edge_list"],
                "png_path": png_path,
                "interactive_path": interactive_path,
                "seed": result["seed"],
                "created_at": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
            }
            save_graph(graph_record)

            generated_ids.append(graph_id)

        except ValueError as e:
            errors.append(f"Graf #{i + 1}: {str(e)}")
        except Exception as e:
            errors.append(f"Graf #{i + 1}: Neočekávaná chyba — {str(e)}")

    if errors and not generated_ids:
        return templates.TemplateResponse(request, "generate.html", {
            "errors": errors,
        })

    if len(generated_ids) == 1:
        return RedirectResponse(url=f"/result/{generated_ids[0]}", status_code=303)
    else:
        return RedirectResponse(url=f"/export?new=true&errors={len(errors)}", status_code=303)


@app.post("/import-tg")
async def import_tg_post(
    request: Request,
    tg_content: str = Form(""),
    directed: bool = Form(False),
):
    """Importuje existující .tg definici grafu, spočítá vlastnosti a algoritmy a uloží do DB."""
    if not tg_content.strip():
        return templates.TemplateResponse(request, "generate.html", {
            "errors": ["Vložte prosím obsah .tg souboru."],
        })

    try:
        parsed = parse_tg(tg_content, directed=directed)
        G = parsed["graph"]
        graph_id = str(uuid.uuid4())

        png_path = render_graph_png(G, graph_id)
        interactive_path = render_graph_interactive(G, graph_id)
        props = graph_properties(G)

        algos = {}
        if G.number_of_nodes() >= 2:
            nodes = sorted(G.nodes())
            algos["shortest_path"] = shortest_path_dijkstra(G, nodes[0], nodes[-1])
        if not directed:
            algos["mst"] = minimum_spanning_tree(G)
        if directed:
            algos["topological_sort"] = topological_sort(G)
        algos["bipartite"] = is_bipartite_check(G)

        config_dict = {
            "node_count": parsed["node_count"],
            "edge_count": parsed["edge_count"],
            "directed": directed,
            "weighted": parsed["weighted"],
            "connected": props.get("is_connected", False),
            "acyclic": nx.is_directed_acyclic_graph(G) if directed else nx.is_forest(G),
            "bipartite": algos["bipartite"].get("is_bipartite", False),
            "seed": None,
        }

        graph_record = {
            "graph_id": graph_id,
            "config": config_dict,
            "properties": props,
            "algorithms": algos,
            "adjacency_matrix": parsed["adjacency_matrix"],
            "edge_list": parsed["edge_list"],
            "png_path": png_path,
            "interactive_path": interactive_path,
            "seed": None,
            "created_at": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
        }
        save_graph(graph_record)
        return RedirectResponse(url=f"/result/{graph_id}", status_code=303)

    except ValueError as e:
        return templates.TemplateResponse(request, "generate.html", {
            "errors": [str(e)],
        })
    except Exception as e:
        return templates.TemplateResponse(request, "generate.html", {
            "errors": [f"Chyba při importu .tg: {str(e)}"],
        })


@app.get("/result/{graph_id}", response_class=HTMLResponse)
async def result_page(request: Request, graph_id: str):
    """Výsledky — graf + řešení."""
    graph_data = get_graph(graph_id)
    if not graph_data:
        return templates.TemplateResponse(request, "index.html", {
            "error": "Graf nebyl nalezen.",
            "total_graphs": count_graphs(),
        })

    node_count = graph_data.get("properties", {}).get("node_count", 0)
    return templates.TemplateResponse(request, "result.html", {
        "graph": graph_data,
        "tg_content": export_to_tg(graph_data, use_letters=True),
        "nodes": list(range(node_count)),
    })


@app.get("/export", response_class=HTMLResponse)
async def export_page(request: Request):
    """Přehled exportovaných zadání."""
    return templates.TemplateResponse(request, "export.html", {
        "graphs": get_all_graphs(),
    })


@app.post("/export/download")
async def export_download(request: Request, format: str = Form("csv")):
    """Stáhne CSV/JSON/.TG ZIP pro UIS."""
    graphs_list = list(get_all_graphs().values())

    if format == "json":
        content = export_to_json(graphs_list)
        media_type = "application/json"
        filename = "grafy_export.json"
        return StreamingResponse(
            io.BytesIO(content.encode("utf-8")),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    elif format == "tg":
        import zipfile
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for i, graph_data in enumerate(graphs_list):
                tg_content = export_to_tg(graph_data)
                zf.writestr(f"graf_{i+1}.tg", tg_content)
        memory_file.seek(0)
        return StreamingResponse(
            memory_file,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=grafy_export_tg.zip"}
        )
    else:
        content = export_to_csv(graphs_list)
        media_type = "text/csv"
        filename = "grafy_export.csv"
        return StreamingResponse(
            io.BytesIO(content.encode("utf-8")),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )


@app.get("/api/graph/{graph_id}/tg")
async def api_graph_tg(graph_id: str, use_letters: bool = True, download: bool = True):
    """Stáhne nebo zobrazí .tg soubor pro jeden konkrétní graf."""
    graph_data = get_graph(graph_id)
    if not graph_data:
        return JSONResponse({"error": "Graf nenalezen"}, status_code=404)

    tg_content = export_to_tg(graph_data, use_letters=use_letters)
    headers = {}
    if download:
        headers["Content-Disposition"] = f"attachment; filename=graf_{graph_id[:8]}.tg"
    return PlainTextResponse(tg_content, headers=headers)


@app.get("/api/graph/{graph_id}/shortest_path")
async def api_graph_shortest_path(graph_id: str, source: int = 0, target: int = 1):
    """Spočítá nejkratší cestu mezi libovolnými dvěma uzly daného grafu."""
    graph_data = get_graph(graph_id)
    if not graph_data:
        return JSONResponse({"error": "Graf nenalezen"}, status_code=404)

    G = _reconstruct_graph(graph_data)
    if source not in G.nodes() or target not in G.nodes():
        return JSONResponse({"error": "Zadaný uzel v grafu neexistuje."}, status_code=400)

    sp = shortest_path_dijkstra(G, source, target)
    return sp


@app.get("/api/graph/{graph_id}")
async def api_graph(graph_id: str):
    """JSON endpoint pro interaktivní Pyvis refresh a nativní SVG zobrazení."""
    graph_data = get_graph(graph_id)
    if not graph_data:
        return JSONResponse({"error": "Graf nenalezen"}, status_code=404)

    G = _reconstruct_graph(graph_data)
    
    graph_payload = {
        "nodes": [int(n) for n in G.nodes()],
        "edges": [
            {
                "source": int(u),
                "target": int(v),
                "weight": G[u][v].get("weight", None)
            }
            for u, v in G.edges()
        ],
        "directed": G.is_directed(),
        "weighted": nx.is_weighted(G),
    }

    # Vrať vše kromě graph_obj (není serializovatelný)
    return {
        "graph_id": graph_data["graph_id"],
        "config": graph_data["config"],
        "properties": graph_data["properties"],
        "algorithms": graph_data["algorithms"],
        "adjacency_matrix": graph_data["adjacency_matrix"],
        "edge_list": graph_data["edge_list"],
        "png_path": graph_data["png_path"],
        "interactive_path": graph_data["interactive_path"],
        "seed": graph_data["seed"],
        "created_at": graph_data.get("created_at", ""),
        "graph_data_vis": graph_payload,
        "positions": graph_data.get("node_positions", None)
    }


@app.post("/api/graph/{graph_id}/delete")
async def api_graph_delete(request: Request, graph_id: str):
    """Smaže vygenerovaný graf z databáze i ze složky statických souborů."""
    delete_graph(graph_id)
    _cleanup_graph_files(graph_id)
        
    # Pokud byl požadavek ajaxový (fetch), vrátíme JSON
    if request.headers.get("accept") == "application/json":
        return JSONResponse({"status": "deleted"})
        
    # Jinak přesměrujeme zpět
    return RedirectResponse(url="/export", status_code=303)


@app.post("/api/graphs/delete-all")
async def api_graphs_delete_all(request: Request):
    """Smaže všechny vygenerované grafy z databáze a uklidí statické soubory."""
    all_graphs = get_all_graphs()
    for gid in all_graphs.keys():
        _cleanup_graph_files(gid)
    deleted_count = delete_all_graphs()

    if request.headers.get("accept") == "application/json":
        return JSONResponse({"status": "deleted_all", "count": deleted_count})

    return RedirectResponse(url="/export", status_code=303)


@app.post("/api/graph/{graph_id}/save_png")
async def api_graph_save_png(request: Request, graph_id: str):
    """Uloží nový náhledový obrázek (base64) na server ze SVG editoru."""
    if not get_graph(graph_id):
        return JSONResponse({"error": "Graph not found"}, status_code=404)
        
    try:
        data = await request.json()
        image_b64 = data.get("image", "")
        positions = data.get("positions")
        
        if positions:
            save_positions(graph_id, positions)
            
        if "," in image_b64:
            header, encoded = image_b64.split(",", 1)
        else:
            encoded = image_b64
            
        image_data = base64.b64decode(encoded)
        filepath = os.path.join(GRAPHS_DIR, f"{graph_id}.png")
        with open(filepath, "wb") as f:
            f.write(image_data)
            
        return {"status": "success"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ============================================================================
# VIZUALIZACE PRŮCHODU ALGORITMŮ
# ============================================================================

@app.get("/visualize/{graph_id}", response_class=HTMLResponse)
async def visualize_page(request: Request, graph_id: str):
    """Stránka s vizualizací průchodu algoritmem."""
    graph_data = get_graph(graph_id)
    if not graph_data:
        return templates.TemplateResponse(request, "index.html", {
            "error": "Graf nebyl nalezen.",
            "total_graphs": count_graphs(),
        })

    # Dostupné algoritmy závisí na typu grafu
    G = _reconstruct_graph(graph_data)
    available_algos = []

    if not G.is_directed() and nx.is_connected(G):
        available_algos.append({"id": "kruskal", "name": "Kruskalův algoritmus (MST)"})
        available_algos.append({"id": "boruvka", "name": "Borůvkův algoritmus (MST)"})

    if G.number_of_nodes() >= 2:
        available_algos.append({"id": "dijkstra", "name": "Dijkstrův algoritmus (nejkratší cesta)"})

    available_algos.append({"id": "bfs", "name": "BFS (prohledávání do šířky)"})
    available_algos.append({"id": "dfs", "name": "DFS (prohledávání do hloubky)"})

    return templates.TemplateResponse(request, "visualize.html", {
        "graph": graph_data,
        "nodes": sorted(G.nodes()),
        "available_algos": available_algos,
    })


@app.get("/api/visualize/{graph_id}/{algorithm}")
async def api_visualize(graph_id: str, algorithm: str, source: int = None, target: int = None):
    """JSON API — vrací kroky pro zvolený algoritmus."""
    graph_data = get_graph(graph_id)
    if not graph_data:
        return JSONResponse({"error": "Graf nenalezen"}, status_code=404)

    G = _reconstruct_graph(graph_data)
    nodes = sorted(G.nodes())

    # Fallback to defaults if none provided or out of bounds
    if source is None or source not in nodes:
        source = nodes[0]
    if target is None or target not in nodes:
        target = nodes[-1]

    # Spočítej kroky
    if algorithm == "kruskal":
        result = kruskal_steps(G)
    elif algorithm == "boruvka":
        result = boruvka_steps(G)
    elif algorithm == "dijkstra":
        result = dijkstra_steps(G, source, target)
    elif algorithm == "bfs":
        result = bfs_steps(G, source)
    elif algorithm == "dfs":
        result = dfs_steps(G, source)
    else:
        return JSONResponse({"error": f"Neznámý algoritmus: {algorithm}"}, status_code=400)

    if result.get("error"):
        return JSONResponse({"error": result["error"]}, status_code=400)

    # Přidej informace o grafu pro vykreslení
    return {
        "algorithm_name": algorithm,
        "graph_data": {
            "nodes": [int(n) for n in nodes],
            "edges": [{"source": int(u), "target": int(v), "weight": G[u][v].get("weight", None)} for u, v in G.edges()],
            "directed": G.is_directed(),
            "weighted": nx.is_weighted(G),
            "positions": graph_data.get("node_positions", None)
        },
        "steps": result["steps"]
    }


# ============================================================================
# DOKUMENTACE
# ============================================================================

@app.get("/docs-algorithms", response_class=HTMLResponse)
async def documentation_page(request: Request):
    """Stránka s dokumentací algoritmů."""
    return templates.TemplateResponse(request, "documentation.html", {})

