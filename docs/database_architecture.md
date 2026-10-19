# Architektura databáze (SQLite)

Tento dokument popisuje databázový model implementovaný pro perzistentní uložení generovaných zadání a vysvětluje důvody, které vedly k tomuto konkrétnímu návrhu. Bude sloužit jako skvělý základ pro kapitolu "Architektura aplikace a datový model" ve vaší diplomové práci.

## 1. Proč byla zvolena SQLite?

Pro tento typ aplikace (nástroj pro generování zadání pro učitele) je SQLite tou nejlepší volbou:
*   **Žádný dedikovaný server:** SQLite nevyžaduje instalaci samostatného databázového serveru (jako PostgreSQL nebo MySQL). Je přímo zabudovaná v Pythonu.
*   **Jednoduchost nasazení (Docker):** Databáze je uložena jako jediný soubor (`graphs.db`) v namapovaném diskovém svazku (volume). Zálohování aplikace znamená pouze překopírovat jeden soubor.
*   **Výkon a spolehlivost:** Pro účely jednoho učitele nebo malé skupiny učitelů poskytuje SQLite více než dostatečný výkon a zachovává plnou ACID (Atomicity, Consistency, Isolation, Durability) spolehlivost – data se neztratí ani při náhlém pádu aplikace.
*   **Žádná údržba:** Odpadá správa uživatelů databáze, hesel a portů.

## 2. Návrh schématu (ER model)

Zvolili jsme hybridní přístup: **Relační struktura** pro hlavní entity a vazby, kombinovaná s **JSON blob sloupcemi** pro vysoce variabilní a nestrukturovaná data (jako jsou konfigurace a výsledky algoritmů).

### 2.1 Tabulka `graphs` (Hlavní záznam grafu)

Tato tabulka ukládá základní metadata o každém vygenerovaném grafu.

| Sloupec | Typ | Popis a důvod použití |
| :--- | :--- | :--- |
| `graph_id` | TEXT (PK) | Unikátní UUID (Primary Key). Rychlé vyhledávání. |
| `config_json` | TEXT | Uloženo jako JSON. Pydantic model (`GraphConfig`) generátoru má mnoho volitelných parametrů, které se mohou v budoucnu rozšiřovat. JSON umožňuje snadné ukládání bez nutnosti měnit strukturu databáze při přidání nové funkce generátoru. |
| `properties_json`| TEXT | Uloženo jako JSON. Obsahuje vypočítané vlastnosti (hustota, průměr, stupně uzlů). Opět se vyhýbáme desítkám drobných sloupců pro specifické vlastnosti, čímž udržujeme schéma čisté. |
| `algorithms_json`| TEXT | Uloženo jako JSON. Ukládá výsledky Dijkstry, MST, topologického třídění atd. Každý algoritmus vrací zcela odlišnou strukturu dat, takže normalizace do mnoha relačních tabulek by vedla k zbytečné složitosti (Anti-pattern). |
| `adjacency_matrix`| TEXT | Uloženo jako JSON pole. Rychlé znovunačtení maticové reprezentace pro účely vykreslování v API. |
| `png_path` | TEXT | Relativní cesta ke statickému obrázku vyrenderovanému přes Matplotlib. |
| `interactive_path`| TEXT | Relativní cesta k interaktivnímu HTML přes Pyvis. |
| `seed` | INTEGER | Výchozí bod pro generátor pseudonáhodných čísel. Slouží pro opakovatelnost (reproducibility) generování. |
| `is_directed` | INTEGER | Zrcadlená Boolean (0/1) hodnota z configu pro rychlé filtrování. |
| `is_weighted` | INTEGER | Zrcadlená Boolean (0/1) hodnota z configu pro rychlé filtrování. |
| `node_count` | INTEGER | Denormalizovaná hodnota pro rychlé třídění a filtrování (abychom nemuseli parsovat `properties_json` při dotazu `SELECT * FROM graphs WHERE node_count > 10`). |
| `edge_count` | INTEGER | Denormalizovaná hodnota pro rychlé třídění a filtrování. |
| `created_at` | TEXT | Časová stopa vytvoření. |

### 2.2 Tabulka `graph_edges` (Hrany grafu)

Namísto uložení hran pouze v JSONu jsme je normalizovali do vlastní tabulky. Důvodem je to, že chceme mít možnost graf efektivně "znovu složit" (rekonstruovat instanci `networkx.Graph`) z relačních dat.

| Sloupec | Typ | Popis |
| :--- | :--- | :--- |
| `id` | INTEGER (PK) | Autoincrement klíč. |
| `graph_id` | TEXT (FK) | Odkaz na `graphs(graph_id)` s pravidlem `ON DELETE CASCADE` (smaže-li se graf, smažou se i jeho hrany). |
| `source_node` | INTEGER | Počáteční uzel hrany. |
| `target_node` | INTEGER | Cílový uzel hrany. |
| `weight` | REAL | Váha hrany (NULL pro neohodnocené). |
| `edge_order` | INTEGER | Pořadí vygenerování (důležité pro vizualizační konzistenci). |

> [!NOTE]
> Index `idx_edges_graph` je nad sloupcem `graph_id`, což zajišťuje bleskové načtení všech hran při rekonstrukci `networkx` objektu.

### 2.3 Tabulka `graph_positions` (Pozice uzlů pro UI editor)

Učitelé mohou v UI (Interaktivním editoru) přesouvat uzly, aby graf vypadal vizuálně lépe před finálním exportem, a tyto ručně upravené souřadnice musí zůstat uloženy.

| Sloupec | Typ | Popis |
| :--- | :--- | :--- |
| `id` | INTEGER (PK) | Autoincrement klíč. |
| `graph_id` | TEXT (FK) | Odkaz na graf (`ON DELETE CASCADE`). |
| `node_id` | INTEGER | ID přesouvaného uzlu. |
| `x` | REAL | X-ová souřadnice z D3.js plátna. |
| `y` | REAL | Y-ová souřadnice z D3.js plátna. |

> [!TIP]
> Proč oddělená tabulka a ne prosté přidání do `properties_json`?
> Souřadnice uzlů se updatují nezávisle na zbytku grafu (pomocí AJAX požadavků z vizualizéru). Ukládat je odděleně zabraňuje "race conditions" a umožňuje velmi rychlý update `UPDATE graph_positions SET x=... WHERE graph_id=...` namísto nutnosti načítat celý velký JSON, modifikovat ho a znovu celý ukládat.

## 3. Implementace a architektura kódu

V aplikaci byl implementován vzor **Data Access Object (DAO)** prostřednictvím modulu `database.py`.
*   Zbytek aplikace (`main.py`) vůbec neví, že používá SQLite. Volá pouze abstrakce jako `save_graph(data)`, `get_graph(id)`, `delete_graph(id)`.
*   Tím je docíleno silného oddělení (separation of concerns), a kdybychom v budoucnu chtěli přejít např. na PostgreSQL, budeme upravovat pouze soubor `database.py`.
*   Byl implementován `contextmanager` `get_db()`, který se bezpečně stará o otevírání a zavírání spojení a v případě chyby provádí automatický Rollback, čímž chrání integritu databáze.

Při spuštění algoritmů nebo API dotazů se in-memory objekt `networkx.Graph` dynamicky a velmi rychle **rekonstruuje** z relačních hran (tabulka `graph_edges`), čímž se vyhneme problému se serializací komplexních Python objektů do databáze.
