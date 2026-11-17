# Architektura databáze (SQLite)

Tento dokument popisuje databázový model implementovaný pro perzistentní uložení generovaných zadání a vysvětluje důvody, které vedly k tomuto konkrétnímu návrhu. Slouží jako podklad pro kapitolu „Datový model" v diplomové práci.

## 1. Proč byla zvolena SQLite?

Pro tento typ aplikace (nástroj pro generování a správu zadání pro vyučující) je SQLite optimální volbou:
*   **Žádný dedikovaný databázový server:** SQLite nevyžaduje instalaci ani správu samostatného serveru (jako PostgreSQL nebo MySQL) a je přímo součástí standardní knihovny jazyka Python (`sqlite3`).
*   **Jednoduchost nasazení (Docker):** Databáze je uložena jako jediný soubor (`graphs.db`) v namapovaném diskovém svazku (Docker volume) a využívá žurnálovací režim **WAL (`Write-Ahead Logging`)** pro rychlé souběžné čtení.
*   **Spolehlivost a automatická migrace:** Poskytuje plnou ACID transakční integritu. Při startu aplikace (`init_db()`) probíhá automatická kontrola schématu, která v případě starší verze databáze bezpečně doplní nové sloupce (např. sloupec `tag`) příkazem `ALTER TABLE`.

## 2. Návrh schématu (ER model)

Zvolili jsme hybridní přístup: **relační struktura** pro hlavní entity, filtrovací atributy a vazby, kombinovaná s **JSON sloupci** pro hierarchické výstupy algoritmů.

### 2.1 Tabulka `graphs` (Hlavní záznam grafu)

Tato tabulka ukládá metadata, konfiguraci a výsledky algoritmů pro každý vygenerovaný nebo naimportovaný graf.

| Sloupec | Typ | Popis a důvod použití |
| :--- | :--- | :--- |
| `graph_id` | TEXT (PK) | Unikátní UUID (Primary Key). |
| `config_json` | TEXT | Uloženo jako JSON. Serializovaný model `GraphConfig` včetně didaktických příznaků (`unique_weights`, `allow_negative_edge`, `force_bridge`). |
| `properties_json`| TEXT | Uloženo jako JSON. Vypočítané vlastnosti grafu (hustota, průměr, stupňová posloupnost, extrémy). |
| `algorithms_json`| TEXT | Uloženo jako JSON. Výsledky všech spuštěných algoritmů (Dijkstra, Bellman-Ford, MST, Max-Flow, barvení, Euler, Hamilton, komponenty/mosty, topologické třídění). |
| `adjacency_matrix`| TEXT | Uloženo jako JSON pole pro okamžité zobrazení matice sousednosti. |
| `png_path` | TEXT | Relativní cesta ke statickému PNG obrázku vyrenderovanému přes Matplotlib (s duálními popisky `A (0)`). |
| `interactive_path`| TEXT | Relativní cesta k interaktivnímu HTML souboru vygenerovanému knihovnou Pyvis. |
| `seed` | INTEGER | Semínko generátoru pseudonáhodných čísel pro plnou reprodukovatelnost. |
| `is_directed` | INTEGER | Denormalizovaná Boolean (0/1) hodnota z konfigurace pro rychlé filtrování. |
| `is_weighted` | INTEGER | Denormalizovaná Boolean (0/1) hodnota z konfigurace pro rychlé filtrování. |
| `node_count` | INTEGER | Denormalizovaný počet vrcholů pro rychlé řazení a filtrování. |
| `edge_count` | INTEGER | Denormalizovaný počet hran. |
| `created_at` | TEXT | Časové razítko vytvoření záznamu. |
| `tag` | TEXT | Uživatelský štítek/kategorie (např. `Cvičení 2`, `Písemka A`, `Výuka - kruskal`) umožňující filtrování a dávkový export podle skupin. |

### 2.2 Tabulka `graph_edges` (Hrany grafu)

Hrany jsou normalizovány do vlastní relační tabulky, aby bylo možné graf kdykoliv rychle zrekonstruovat do objektu `networkx.Graph` nebo `networkx.DiGraph`.

| Sloupec | Typ | Popis |
| :--- | :--- | :--- |
| `id` | INTEGER (PK) | Autoincrement primární klíč. |
| `graph_id` | TEXT (FK) | Cizí klíč na `graphs(graph_id)` s pravidlem `ON DELETE CASCADE`. |
| `source_node` | INTEGER | Počáteční vrchol hrany. |
| `target_node` | INTEGER | Koncový vrchol hrany. |
| `weight` | REAL | Váha hrany (`NULL` pro neohodnocené grafy). |
| `edge_order` | INTEGER | Pořadí vygenerování hrany (pro konzistentní označení `h1, h2...` ve formátu `.tg`). |

> [!NOTE]
> Nad sloupcem `graph_id` je vytvořen index `idx_edges_graph`, který zajišťuje okamžité načtení všech hran při rekonstrukci grafu.

### 2.3 Tabulka `graph_positions` (Pozice uzlů z grafického editoru)

Vyučující může v interaktivním SVG editoru přesouvat uzly myší tak, aby se hrany nekřížily, a uložit toto rozložení pro tisk písemky.

| Sloupec | Typ | Popis |
| :--- | :--- | :--- |
| `id` | INTEGER (PK) | Autoincrement primární klíč. |
| `graph_id` | TEXT (FK) | Cizí klíč na `graphs(graph_id)` s pravidlem `ON DELETE CASCADE`. |
| `node_id` | INTEGER | Číselný index přesouvaného uzlu. |
| `x` | REAL | X-ová souřadnice z SVG plátna. |
| `y` | REAL | Y-ová souřadnice z SVG plátna. |

## 3. Implementace a architektura přístupu k datům (DAO)

V modulu `app/database.py` je implementován návrhový vzor **Data Access Object (DAO)**:
*   Řídicí vrstva (`main.py`) neobsahuje žádné SQL dotazy a volá výhradně vysokoúrovňové funkce `save_graph()`, `get_graph()`, `get_all_graphs(tag=...)`, `update_graph_tag()`, `get_all_tags()`, `save_positions()`, `delete_graph()` a `delete_all_graphs()`.
*   Správu transakcí zajišťuje kontextový manažer `get_db()`, který automaticky provádí `COMMIT` po úspěšné operaci a `ROLLBACK` v případě výjimky.
