"""
database.py — SQLite persistence vrstva pro aplikaci Teorie Grafů

Implementuje Data Access Object (DAO) pattern pro čisté oddělení
databázové logiky od zbytku aplikace. Všechny operace s databází
procházejí výhradně přes tento modul.

Schéma databáze:
    graphs          — hlavní tabulka grafů (metadata, konfigurace, vlastnosti)
    graph_edges     — hrany grafu (source, target, weight)
    graph_positions — uložené pozice uzlů (x, y) pro statický editor
    graph_algorithms — výsledky algoritmů (JSON blob per algorithm)

Proč SQLite?
    - Nevyžaduje žádný server ani instalaci (je součástí Pythonu)
    - Ideální pro jednoúčelové lokální aplikace (Docker Desktop)
    - Plně ACID kompatibilní — data přežijí restart / pád aplikace
    - Snadná záloha — celá DB je jeden soubor (graphs.db)
"""

import os
import json
import sqlite3
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================================================
# KONFIGURACE
# ============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if os.environ.get("TESTING") == "1":
    DB_PATH = os.path.join(BASE_DIR, "data", "test_graphs.db")
else:
    DB_PATH = os.path.join(BASE_DIR, "data", "graphs.db")


# ============================================================================
# PŘIPOJENÍ K DATABÁZI
# ============================================================================

@contextmanager
def get_db():
    """
    Context manager pro bezpečné připojení k SQLite.

    Použití:
        with get_db() as conn:
            conn.execute("SELECT ...")

    Proč context manager?
        - Automaticky commituje při úspěchu
        - Automaticky rollbackuje při chybě
        - Vždy zavře spojení (i při výjimce)
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Vrací dict-like řádky místo tuplů
    conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging (lepší výkon)
    conn.execute("PRAGMA foreign_keys=ON")   # Kontrola cizích klíčů
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ============================================================================
# INICIALIZACE SCHÉMATU
# ============================================================================

def init_db():
    """
    Vytvoří databázové tabulky, pokud neexistují.

    Voláno při startu aplikace. Používá IF NOT EXISTS,
    takže je bezpečné volat opakovaně.
    """
    with get_db() as conn:
        conn.executescript("""
            -- ===============================================================
            -- Tabulka GRAPHS: hlavní entita — jeden vygenerovaný graf
            -- ===============================================================
            -- Uchovává metadata, konfigurační parametry (jako JSON),
            -- vypočtené vlastnosti, matici sousednosti a cesty k souborům.
            --
            -- Proč JSON pro config/properties/algorithms?
            --   Tyto struktury jsou volitelně vnořené a heterogenní.
            --   Normalizace by vedla k desítkám tabulek bez jasného přínosu.
            --   JSON umožňuje snadné rozšíření bez migrace schématu.
            -- ===============================================================
            CREATE TABLE IF NOT EXISTS graphs (
                graph_id         TEXT PRIMARY KEY,
                config_json      TEXT NOT NULL,           -- GraphConfig jako JSON
                properties_json  TEXT NOT NULL,           -- Vlastnosti grafu jako JSON
                algorithms_json  TEXT NOT NULL DEFAULT '{}', -- Výsledky algoritmů jako JSON
                adjacency_matrix TEXT NOT NULL,           -- Matice sousednosti jako JSON [[...]]
                png_path         TEXT,                    -- Cesta k PNG souboru
                interactive_path TEXT,                    -- Cesta k interaktivnímu HTML
                seed             INTEGER,                 -- Seed pro reprodukovatelnost
                is_directed      INTEGER NOT NULL DEFAULT 0,  -- BOOLEAN (0/1)
                is_weighted      INTEGER NOT NULL DEFAULT 1,  -- BOOLEAN (0/1)
                node_count       INTEGER NOT NULL,        -- Denormalizováno pro rychlé filtrování
                edge_count       INTEGER NOT NULL,        -- Denormalizováno pro rychlé filtrování
                created_at       TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );

            -- ===============================================================
            -- Tabulka GRAPH_EDGES: hrany grafu
            -- ===============================================================
            -- Normalizovaná tabulka hran. Každý řádek = jedna hrana.
            -- Umožňuje efektivní dotazy typu:
            --   "Najdi všechny hrany grafu X s váhou > 5"
            --   "Seřaď hrany podle váhy"
            -- ===============================================================
            CREATE TABLE IF NOT EXISTS graph_edges (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                graph_id    TEXT NOT NULL REFERENCES graphs(graph_id) ON DELETE CASCADE,
                source_node INTEGER NOT NULL,
                target_node INTEGER NOT NULL,
                weight      REAL,                         -- NULL pro neohodnocené grafy
                edge_order  INTEGER NOT NULL DEFAULT 0    -- Pořadí hrany (h1, h2, ...)
            );

            CREATE INDEX IF NOT EXISTS idx_edges_graph ON graph_edges(graph_id);

            -- ===============================================================
            -- Tabulka GRAPH_POSITIONS: uložené pozice uzlů
            -- ===============================================================
            -- Uchovává ručně upravené pozice z D3.js/SVG editoru.
            -- Uzel je identifikován číslem (node_id), pozice jsou x/y
            -- souřadnice v SVG prostoru.
            --
            -- Proč vlastní tabulka?
            --   Pozice se mění nezávisle na grafu (učitel je přesouvá).
            --   Oddělení umožňuje aktualizaci pozic bez přepisu celého grafu.
            -- ===============================================================
            CREATE TABLE IF NOT EXISTS graph_positions (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                graph_id TEXT NOT NULL REFERENCES graphs(graph_id) ON DELETE CASCADE,
                node_id  INTEGER NOT NULL,
                x        REAL NOT NULL,
                y        REAL NOT NULL,
                UNIQUE(graph_id, node_id)                 -- Každý uzel má max 1 pozici
            );

            CREATE INDEX IF NOT EXISTS idx_positions_graph ON graph_positions(graph_id);
        """)


# ============================================================================
# CRUD OPERACE — GRAFY
# ============================================================================

def save_graph(graph_data: dict) -> None:
    """
    Uloží kompletní graf do databáze (INSERT OR REPLACE).

    Args:
        graph_data: dict se strukturou odpovídající graphs_store
            Klíče: graph_id, config, properties, algorithms,
                   adjacency_matrix, edge_list, png_path,
                   interactive_path, seed, created_at
    """
    config = graph_data.get("config", {})
    properties = graph_data.get("properties", {})

    with get_db() as conn:
        # Hlavní záznam grafu
        conn.execute("""
            INSERT OR REPLACE INTO graphs
                (graph_id, config_json, properties_json, algorithms_json,
                 adjacency_matrix, png_path, interactive_path, seed,
                 is_directed, is_weighted, node_count, edge_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            graph_data["graph_id"],
            json.dumps(config, ensure_ascii=False),
            json.dumps(properties, ensure_ascii=False, default=str),
            json.dumps(graph_data.get("algorithms", {}), ensure_ascii=False, default=str),
            json.dumps(graph_data.get("adjacency_matrix", []), default=str),
            graph_data.get("png_path"),
            graph_data.get("interactive_path"),
            graph_data.get("seed"),
            1 if config.get("directed") else 0,
            1 if config.get("weighted", True) else 0,
            properties.get("node_count", 0),
            properties.get("edge_count", 0),
            graph_data.get("created_at", datetime.now().strftime("%d.%m.%Y %H:%M:%S")),
        ))

        # Hrany — nejdřív smaž staré, pak vlož nové
        graph_id = graph_data["graph_id"]
        conn.execute("DELETE FROM graph_edges WHERE graph_id = ?", (graph_id,))
        edge_list = graph_data.get("edge_list", [])
        for idx, edge in enumerate(edge_list):
            conn.execute("""
                INSERT INTO graph_edges (graph_id, source_node, target_node, weight, edge_order)
                VALUES (?, ?, ?, ?, ?)
            """, (
                graph_id,
                edge.get("source"),
                edge.get("target"),
                edge.get("weight"),
                idx + 1,
            ))


def get_graph(graph_id: str) -> Optional[dict]:
    """
    Načte graf z databáze a vrátí ho ve formátu kompatibilním
    s původním graphs_store dict.

    Returns:
        dict nebo None pokud graf neexistuje
    """
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM graphs WHERE graph_id = ?", (graph_id,)
        ).fetchone()

        if not row:
            return None

        # Načti hrany
        edges = conn.execute(
            "SELECT source_node, target_node, weight, edge_order "
            "FROM graph_edges WHERE graph_id = ? ORDER BY edge_order",
            (graph_id,)
        ).fetchall()

        edge_list = [
            {"source": e["source_node"], "target": e["target_node"], "weight": e["weight"]}
            for e in edges
        ]

        # Načti pozice
        positions = load_positions(graph_id, conn=conn)

        # Sestav dict kompatibilní s graphs_store
        result = {
            "graph_id": row["graph_id"],
            "config": json.loads(row["config_json"]),
            "properties": json.loads(row["properties_json"]),
            "algorithms": json.loads(row["algorithms_json"]),
            "adjacency_matrix": json.loads(row["adjacency_matrix"]),
            "edge_list": edge_list,
            "png_path": row["png_path"],
            "interactive_path": row["interactive_path"],
            "seed": row["seed"],
            "created_at": row["created_at"],
        }

        if positions:
            result["node_positions"] = positions

        return result


def get_all_graphs() -> dict:
    """
    Načte všechny grafy z databáze.

    Returns:
        dict[graph_id -> graph_data] — stejná struktura jako graphs_store
    """
    with get_db() as conn:
        rows = conn.execute(
            "SELECT graph_id FROM graphs ORDER BY created_at DESC"
        ).fetchall()

    # Načti jednotlivé grafy (každý potřebuje svůj JOIN)
    result = {}
    for row in rows:
        graph_data = get_graph(row["graph_id"])
        if graph_data:
            result[graph_data["graph_id"]] = graph_data
    return result


def delete_graph(graph_id: str) -> bool:
    """
    Smaže graf z databáze (CASCADE smaže i hrany a pozice).

    Returns:
        True pokud graf existoval a byl smazán
    """
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM graphs WHERE graph_id = ?", (graph_id,)
        )
        return cursor.rowcount > 0


def delete_all_graphs() -> int:
    """
    Smaže všechny grafy z databáze (CASCADE smaže i všechny hrany a pozice).

    Returns:
        Počet smazaných grafů
    """
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM graphs")
        return cursor.rowcount


def count_graphs() -> int:
    """Vrátí celkový počet grafů v databázi."""
    with get_db() as conn:
        row = conn.execute("SELECT COUNT(*) as cnt FROM graphs").fetchone()
        return row["cnt"]



# ============================================================================
# CRUD OPERACE — POZICE UZLŮ
# ============================================================================

def save_positions(graph_id: str, positions: dict) -> None:
    """
    Uloží/aktualizuje pozice uzlů pro daný graf.

    Args:
        graph_id: ID grafu
        positions: dict {node_id_str: {"x": float, "y": float}, ...}
    """
    with get_db() as conn:
        # Smaž staré pozice
        conn.execute(
            "DELETE FROM graph_positions WHERE graph_id = ?", (graph_id,)
        )

        # Vlož nové
        for node_id_str, coords in positions.items():
            conn.execute("""
                INSERT INTO graph_positions (graph_id, node_id, x, y)
                VALUES (?, ?, ?, ?)
            """, (
                graph_id,
                int(node_id_str),
                coords["x"],
                coords["y"],
            ))


def load_positions(graph_id: str, conn=None) -> Optional[dict]:
    """
    Načte uložené pozice uzlů.

    Returns:
        dict {node_id_str: {"x": float, "y": float}} nebo None
    """
    def _fetch(c):
        rows = c.execute(
            "SELECT node_id, x, y FROM graph_positions WHERE graph_id = ?",
            (graph_id,)
        ).fetchall()
        if not rows:
            return None
        return {str(r["node_id"]): {"x": r["x"], "y": r["y"]} for r in rows}

    if conn:
        return _fetch(conn)

    with get_db() as conn:
        return _fetch(conn)
