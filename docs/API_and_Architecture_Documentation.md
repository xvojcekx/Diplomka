# Architektura a API Dokumentace Aplikace
(Dokument pro finální kompletaci diplomové práce)

## 1. Architektura Aplikace
Aplikace je postavena na moderním asynchronním webovém rámci **FastAPI** v jazyce **Python**. Využívá knihovnu **NetworkX** pro komplexní generování, modifikace a analýzu grafů. Jako datové úložiště byla zvolena vestavěná relační databáze **SQLite** v režimu WAL (`Write-Ahead Logging`), která vyhovuje potřebám kontejnerizovaného nasazení a perzistentního uchování vygenerovaných grafů, jejich pozic a štítků.

Architektonicky se aplikace dělí na čtyři klíčové vrstvy (*Separation of Concerns*):
- **Prezentační vrstva (Jinja2 Templates, Bootstrap 5, SVG/Pyvis):** Zajišťuje frontendové zobrazení, interaktivní vykreslování grafů se sjednocenými popisky uzlů (`A (0)`, `B (1)`…), krokování algoritmů a tiskové pracovní listy písemek (`@media print`).
- **Aplikační a řídicí vrstva (FastAPI — `main.py`):** Obsluhuje HTTP požadavky (HTML stránky i REST API endpointy) a validuje uživatelské vstupy pomocí modelů knihovny **Pydantic** (`models.py`).
- **Doménová a výpočetní vrstva (`generator.py`, `solver.py`, `scenarios.py`, `grader.py`, `exporter.py`):** Zapouzdřuje matematickou logiku generování grafů s didaktickými garancemi, výpočet 10 grafových algoritmů, generování kontextových slovních úloh a tabulek pro písemky, sémantickou validaci víceznačných studentských řešení a obousměrný převod formátu `.tg`.
- **Datová vrstva (SQLite DAO — `database.py`):** Zajišťuje trvalé uložení struktury grafů, pozic uzlů, štítků (`tag`) a výsledků algoritmů pomocí návrhového vzoru DAO (*Data Access Object*).

### Adresářová struktura
```text
aplikace_ver_2/
├── app/
│   ├── main.py            # Vstupní bod, FastAPI routery a definice endpointů
│   ├── database.py        # Logika pro ukládání a načítání z SQLite DB (DAO)
│   ├── generator.py       # Generátor grafů a didaktických garancí nad NetworkX
│   ├── models.py          # Pydantic modely definující vstupní/výstupní schémata
│   ├── solver.py          # Implementace a extrakce kroků grafových algoritmů
│   ├── scenarios.py       # Didaktický generátor slovních úloh a tiskových písemek
│   ├── grader.py          # Sémantický validátor studentských odpovědí (Grader v2)
│   ├── exporter.py        # Export a import formátu .tg, CSV, JSON, ZIP
│   ├── templates/         # HTML šablony (Jinja2: index, teaching, exam, generate, result, export, visualize, documentation)
│   └── static/            # CSS styly, JS SVG editor/krokování a vygenerované PNG/HTML grafy
├── tests/                 # Automatizované testy (Pytest — 68 testů)
│   ├── conftest.py        # Konfigurace testovacího prostředí (TESTING=1)
│   ├── test_api.py        # Integrační testy FastAPI endpointů, výuky a písemek
│   ├── test_generator.py  # Unit testy generátoru a didaktických garancí
│   ├── test_solver.py     # Unit testy správnosti algoritmů a validátoru
│   └── test_independent_verification.py  # Nezávislé ověření (hrubá síla, vlastní Edmonds–Karp)
├── docs/                  # Technická dokumentace a podklady pro text diplomové práce
├── docker-compose.yml     # Konfigurace kontejnerů a persistentních volumes
├── Dockerfile             # Definice Docker image
└── requirements.txt       # Závislosti aplikace
```

## 2. Návrh Databáze (SQLite)
Je použita hybridní relační struktura tří tabulek pro uložení normalizované topologie grafu i strukturovaných JSON výstupů algoritmů:

1. **`graphs` (Hlavní tabulka pro metadata a výsledky)**
   - `graph_id` (TEXT, PK): Unikátní UUID identifikátor grafu.
   - `config_json` (TEXT/JSON): Vstupní parametry (`GraphConfig`) včetně didaktických voleb (`unique_weights`, `allow_negative_edge`, `force_bridge`).
   - `properties_json` (TEXT/JSON): Vypočtené invarianty grafu (souvislost, hustota, průměr, stupňová posloupnost).
   - `algorithms_json` (TEXT/JSON): Výsledky algoritmů (Dijkstra, Bellman-Ford, Kruskal MST, Max-Flow/Min-Cut, barvení, Euler, Hamilton, komponenty/mosty, topologické řazení).
   - `adjacency_matrix` (TEXT/JSON): Matice sousednosti.
   - `png_path`, `interactive_path` (TEXT): Cesty k vygenerovaným vizualizacím.
   - `seed` (INTEGER): Semínko pseudonáhodného generátoru pro plnou reprodukovatelnost.
   - `is_directed`, `is_weighted`, `node_count`, `edge_count` (INTEGER): Denormalizované sloupce pro rychlé indexované dotazy.
   - `created_at` (TEXT): Časové razítko vytvoření.
   - `tag` (TEXT): Uživatelský štítek/kategorie (např. `Cvičení 3`, `Písemka A`) pro rychlé filtrování a hromadný export.

2. **`graph_edges` (Uložení samotné struktury grafu)**
   - `id` (INTEGER, PK): Primární klíč.
   - `graph_id` (TEXT, FK): Cizí klíč do tabulky `graphs` (`ON DELETE CASCADE`).
   - `source_node` (INTEGER), `target_node` (INTEGER): Zdrojový a cílový vrchol hrany.
   - `weight` (REAL): Váha hrany (`NULL` pro neohodnocené grafy).
   - `edge_order` (INTEGER): Pořadí hrany.

3. **`graph_positions` (Uložení manuálních souřadnic uzlů)**
   - `id` (INTEGER, PK): Primární klíč.
   - `graph_id` (TEXT, FK): Cizí klíč do tabulky `graphs` (`ON DELETE CASCADE`).
   - `node_id` (INTEGER): Index vrcholu.
   - `x` (REAL), `y` (REAL): Souřadnice uzlu uložené z interaktivního SVG editoru.

## 3. Přehled stránek a REST API Endpointů

### Webové stránky (GET)
- `/`: Domovská stránka s rozcestníkem a celkovou statistikou uložených grafů.
- `/teaching`: **Výuka — demo**; didaktické předvolby na jedno kliknutí pro okamžité vygenerování typových grafů a písemek.
- `/exam/{graph_id}`: **Tiskový pracovní list písemky** se slovním zadáním, předtištěnou tabulkou pro studenta a přepínatelným autorským řešením pro vyučujícího (podporuje query parametry `scenario`, `source`, `mid`, `target`).
- `/generate`: Pokročilý formulář pro dávkové generování grafů a import existujícího `.tg` souboru.
- `/result/{graph_id}`: Detail vygenerovaného grafu, matice sousednosti, seznam hran, výsledky všech algoritmů, export `.tg` a interaktivní validátor odpovědí studenta.
- `/visualize/{graph_id}`: Interaktivní přehrávač kroků algoritmů (BFS, DFS, Dijkstra, Bellman-Ford, Kruskal, Borůvka) a editor pozic uzlů.
- `/export`: Správa vygenerovaných grafů, filtrování podle štítků (`?tag=...`) a hromadný export (`.tg` ZIP, CSV, JSON).
- `/docs-algorithms`: Výuková dokumentace jednotlivých grafových algoritmů s pseudokódy a rozborem složitosti.

### Funkční a REST API endpointy
- **`POST /teaching/generate`**: Vygeneruje graf podle zvoleného didaktického presetu (`dijkstra`, `dijkstra_stopover`, `kruskal`, `bellman_ford`, `bridges`, `toposort`, `max_flow`), přiřadí štítek a přesměruje přímo na pracovní list písemky `/exam/{id}`.
- **`POST /generate`**: Vygeneruje dávku grafů podle podrobné konfigurace (`GraphConfig`) včetně didaktických přepínačů.
- **`POST /import-tg`**: Zparsuje vložený `.tg` text, zrekonstruuje graf, vykreslí vizualizace, spočítá všechny algoritmy a uloží graf do SQLite.
- **`POST /export/download`**: Vrátí hromadný export vybraných grafů (volitelně filtrovaných podle `tag`) ve formátu CSV, JSON nebo ZIP archivu `.tg` souborů.
- **`GET /api/graph/{graph_id}`**: Vrátí kompletní JSON reprezentaci grafu včetně pozic uzlů.
- **`GET /api/graph/{graph_id}/tg`**: Vrátí nebo stáhne `.tg` definici grafu (s písmenným označením vrcholů `A, B, C...`).
- **`GET /api/graph/{graph_id}/shortest_path`**: Dynamicky přepočítá nejkratší cestu mezi libovolnými uzly `source` a `target`.
- **`POST /api/graph/{graph_id}/grade`**: Sémantický validátor studentských odpovědí (Grader v2) pro minimální kostru, nejkratší cestu a topologické uspořádání.
- **`POST /api/graph/{graph_id}/tag`**: Aktualizuje uživatelský štítek (`tag`) daného grafu.
- **`POST /api/graph/{graph_id}/save_positions`**: Uloží ručně upravené souřadnice uzlů z přehrávače kroků (`/visualize/{id}`) do tabulky `graph_positions` a na serveru přegeneruje čistý tiskový PNG obrázek grafu (bez barevného zvýraznění kroků algoritmu).
- **`POST /api/graph/{graph_id}/save_png`**: Uloží upravené souřadnice uzlů z prohlížeče do tabulky `graph_positions` a přepíše statický PNG náhled grafu.
- **`POST /api/graph/{graph_id}/delete`** a **`POST /api/graphs/delete-all`**: Smaže jeden nebo všechny grafy včetně souvisejících statických souborů.
- **`GET /api/visualize/{graph_id}/{algorithm}`**: Vrátí pole diskrétních kroků zvoleného algoritmu pro animaci na SVG plátně.

## 4. Automatizované testy (Test Suite)
Kritické procesy a výpočty jsou pokryty sadou **68 automatizovaných testů** postavených na knihovně `pytest`. Při nastavení proměnné prostředí `TESTING=1` (v `tests/conftest.py`) běží testy nad izolovanou dočasnou databází `test_graphs.db`.

### Rozdělení testů
1. **`test_solver.py`**
   - Testuje matematickou správnost všech algoritmů (Dijkstra, Bellman-Ford, Kruskal, Borůvka, Ford-Fulkerson Max-Flow/Min-Cut, Welsh-Powell barvení, Eulerovské a Hamiltonovské cesty, komponenty a mosty, topologické řazení, bipartitnost) a sémantický validátor `grader.py`.
2. **`test_generator.py`**
   - Ověřuje dodržení počtu vrcholů, hran, souvislosti (včetně dosažitelnosti cíle u orientovaných grafů), acykličnosti (DAG/strom), bipartitnosti, reprodukovatelnosti pomocí `seed` a didaktických garancí (`unique_weights`, `allow_negative_edge`, `force_bridge`).
3. **`test_api.py`**
   - Integrační end-to-end (E2E) testy všech stránek, REST endpointů, obousměrného `.tg` importu/exportu, štítkování (`tag`) a všech 7 scénářů výukových písemek (`/teaching/generate` a `/exam/{id}`).
4. **`test_independent_verification.py`**
   - Referenční hodnoty nepocházejí z NetworkX: úplné prohledání cest a koster, vlastní Edmondsův–Karpův algoritmus, kontrola vlastností výsledku. Ověřuje také garance generátoru, všech sedm scénářů písemek a uznání všech správných minimálních koster validátorem.
