# Architektura a API Dokumentace Aplikace
(Dokument pro finální kompletaci diplomové práce)

## 1. Architektura Aplikace
Aplikace je postavena na moderním webovém rámci **FastAPI** v jazyce **Python**. Využívá knihovnu **NetworkX** pro komplexní generování, modifikace a analýzu grafů. Jako datové úložiště byla zvolena vestavěná odlehčená databáze **SQLite**, která dokonale vyhovuje potřebám jednoduchého nasazení a persistentního uchování vygenerovaných grafů.

Architektonicky se aplikace dělí na několik klíčových vrstev (Separation of Concerns):
- **Prezentační vrstva (Jinja2 Templates & Bootstrap 5):** Zajišťuje frontendové zobrazení, renderování formulářů a výsledků pomocí responsivního designu.
- **Aplikační vrstva (FastAPI):** Obsluhuje HTTP požadavky (API endpointy i statické stránky), validuje uživatelské vstupy pomocí Pydantic modelů.
- **Logická vrstva (Generátory a Solvery):** Zapouzdřuje složitou matematickou logiku generování grafů, výpočtů a řešení algoritmů.
- **Datová vrstva (SQLite DAO):** Zajišťuje trvalé uložení struktury grafů, pozic uzlů a vypočtených algoritmů. Využívá patternu DAO (Data Access Object).

### Adresářová struktura (Best Practice)
```text
aplikace/
├── app/
│   ├── main.py            # Vstupní bod, FastAPI routery a definice endpointů
│   ├── database.py        # Logika pro ukládání a načítání z SQLite DB (DAO)
│   ├── generator.py       # Obálka nad NetworkX pro generování typů grafů
│   ├── models.py          # Pydantic modely definující vstupní/výstupní schémata
│   ├── solver.py          # Implementace a extrakce kroků grafových algoritmů
│   └── templates/         # HTML šablony (Jinja2)
├── tests/                 # Adresář pro automatizované testy (pytest)
│   ├── conftest.py        # Konfigurace testovacího prostředí
│   ├── test_api.py        # Testy FastAPI endpointů
│   ├── test_generator.py  # Testy generátoru a limitních stavů grafů
│   └── test_solver.py     # Testy správnosti výpočtů algoritmů
├── data/                  # Persistentní složka pro SQLite databázi (graphs.db)
├── static/
│   └── graphs/            # Zde se ukládají vygenerované PNG vizualizace
├── docker-compose.yml     # Konfigurace kontejnerů a volumes
├── Dockerfile             # Definice Docker image
└── requirements.txt       # Závislosti aplikace
```

## 2. Návrh Databáze (SQLite)
Byla použita jednoduchá, ale efektivní struktura využívající 3 tabulek pro uložení dat a metadata vygenerovaných grafů.

1. **`graphs` (Hlavní tabulka pro metadata)**
   - `id` (VARCHAR): Primární klíč, unikátní UUID grafu.
   - `config` (JSON): Vstupní parametry (GraphConfig) použité pro generování.
   - `properties` (JSON): Vypočtené statistiky grafu (souvislost, hustota, atd.).
   - `algorithms` (JSON): Výsledky algoritmů (MST, nejkratší cesty, atd.).
   - `png_path`, `interactive_path` (VARCHAR): Cesty k vygenerovaným vizualizacím.
   - `seed` (INTEGER): Seed použitý k vygenerování (pro reprodukovatelnost).
   - `created_at` (DATETIME): Časové razítko vytvoření.

2. **`graph_edges` (Uložení samotné struktury grafu)**
   - Ukládá jednotlivé hrany grafu.
   - `id` (INTEGER): Primární klíč.
   - `graph_id` (VARCHAR): Cizí klíč do tabulky `graphs`.
   - `source` (INTEGER), `target` (INTEGER): Zdrojový a cílový uzel.
   - `weight` (FLOAT): Váha hrany.

3. **`graph_positions` (Uložení manuálních souřadnic uzlů)**
   - `id` (INTEGER): Primární klíč.
   - `graph_id` (VARCHAR): Cizí klíč.
   - `positions` (JSON): Objekt mapující ID uzlu na souřadnice `{ "0": {"x": 10, "y": 20} }`.

## 3. Logika API (Endpoints)

### Stránky (GET)
- `/`: Domovská stránka obsahující přehled, nedávno generované grafy a obecné statistiky.
- `/generate`: Formulář pro generování nových grafů (umožňuje batchování, omezení vah, vlastností).
- `/result/{graph_id}`: Zobrazí konkrétní vygenerovaný graf (grafika, vlastnosti, kroky algoritmů).
- `/export`: Stránka pro správu vygenerovaných grafů a hromadný export do UIS systému.
- `/docs-algorithms`: Výuková dokumentace ke konkrétním algoritmům, jak fungují, a jak je systém počítá.

### Funkční endpointy
- **`POST /generate`**
  - **Účel**: Generuje novou sadu grafů na základě odeslaného formuláře (`BatchConfig`).
  - **Logika**: 
    1. Validuje vstupy. 
    2. Vygeneruje NetworkX objekty pomocí `generator.py`. 
    3. Vyrenderuje PNG. 
    4. Provede výpočty vlastností a kroků algoritmů. 
    5. Uloží do SQLite a přesměruje uživatele na `/result` nebo zpět na export.
- **`POST /export/download`**
  - **Účel**: Umožňuje stažení celé databáze v předem daném formátu (`csv`, `json`).
- **`GET /api/graph/{graph_id}`**
  - **Účel**: Asynchronní REST endpoint vrací JSON objekt reprezentující graf. Zahrnuje nodes, edges a metadata, vhodný pro Javascriptové knihovny na frontendu (např. D3.js nebo Pyvis).
- **`POST /api/graph/{graph_id}/delete`**
  - **Účel**: Smaže konkrétní graf z databáze (včetně kaskádového smazání hran).
- **`POST /api/graph/{graph_id}/save_png`**
  - **Účel**: Přijímá Base64 string z Canvasu a ukládá ho na server jako PNG soubor grafu.

## 4. Automatizované testy (Test Suite)
Kritické procesy a výpočty jsou pokryty automatizovanými testy postavenými na knihovně `pytest`. Tím je zaručeno, že modifikace kódu do budoucna nerozbijí funkčnost. Testy běží v izolovaném prostředí, kde proměnná `TESTING=1` zaručí, že testy pracují s dočasnou databází v paměti (`test_graphs.db`), nikoliv s ostrou produkční DB.

### Rozdělení testů
1. **`test_solver.py` (39 funkčních testů)**
   - Testuje čistou matematickou logiku nad iterátory NetworkX.
   - Kontroluje spolehlivost algoritmů: Dijkstra, Kruskal, Borůvka, Bipartitnost, Topologické třídění atd.
   - Ověřuje vlastnosti grafů, hledání stupňů uzlů a kontrolu, zda cesty dávají matematický smysl.

2. **`test_generator.py`**
   - Validuje výstupy generátoru. Kontroluje, že vygenerovaný graf (Node Count, Edge Count, Váhy) striktně odpovídá tomu, o co si uživatel ve formuláři požádal.
   - Zahrnuje limity okrajových případů a reprodukovatelnost grafu se stejným Seed číslem.

3. **`test_api.py`**
   - End-to-end (E2E) testování HTTP odpovědí aplikací.
   - Klientská simulace pomocí `FastAPI.TestClient`.
   - Zajišťuje správný chod routování, vracení HTML/JSON podle endpointů a HTTP kódů.
