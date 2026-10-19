# Webová aplikace pro generování úloh z teorie grafů

**Diplomová práce — PEF MENDELU v Brně**  
**Autor:** Bc. Vojtěch Střílka  
**Vedoucí práce:** Ing. Pavel Haluza, Ph.D.

---

## 1. K čemu aplikace slouží

Tato webová aplikace slouží k **automatizovanému generování, analýze, interaktivní vizualizaci a exportu grafových úloh** pro výuku předmětu *Teorie grafů* na Provozně ekonomické fakultě Mendelovy univerzity v Brně (PEF MENDELU).

Řeší klíčový problém přípravy testových zadání: vyučující nemusí ručně vymýšlet grafy, kreslit jejich obrázky a ručně přepočítávat správné výsledky pro každou variantu testu. Aplikace na základě zvolených parametrů vygeneruje požadovaný počet unikátních grafů, automaticky pro ně vypočítá správná řešení referenčních algoritmů a připraví podklady pro přímý import do **Univerzitního informačního systému (UIS MENDELU)**.

---

## 2. Co je již hotovo (Přehled funkcionalit)

### Konfigurovatelný generátor grafů (`app/generator.py`)
* **Dávkové generování (Batching):** Možnost vygenerovat 1 až 50 grafů najednou.
* **Dva režimy zadávání:** Přesný počet uzlů/hran nebo náhodný interval `[min, max]`.
* **Strukturální vlastnosti:**
  * Orientované (`DiGraph`) i neorientované (`Graph`) grafy.
  * Ohodnocené hrany s nastavitelným rozsahem vah `[weight_min, weight_max]` i neohodnocené grafy.
  * Zaručeně souvislé grafy (vytvoření kostry + doplnění náhodných hran).
  * Acyklické grafy — orientované acyklické grafy (**DAG**) a neorientované **stromy**.
  * **Bipartitní** grafy.
* **Reprodukovatelnost:** Podpora `seed` parametru (stejný seed vygeneruje identický graf).

### Výpočetní jádro a algoritmy (`app/solver.py`)
* **Základní invarianty a vlastnosti grafu:** Počet uzlů a hran, orientovanost, souvislost, hustota grafu, průměr grafu (diameter), stupňová posloupnost, extrémy stupňů uzlů a vah hran.
* **Automatické řešení úloh:**
  * **Dijkstrův algoritmus** — nejkratší cesta a její délka (s možností interaktivního přepočtu pro libovolnou dvojici uzlů přímo v detailu grafu).
  * **Kruskalův algoritmus** — minimální kostra grafu (MST) a její celková váha.
  * **Topologické třídění** — ověření acykličnosti a výpis topologického uspořádání pro orientované grafy.
  * **Test bipartitnosti** — rozdělení uzlů do dvou disjunktních množin $U$ a $V$.
* **Krokování algoritmů pro výuku:** Detailní generování jednotlivých kroků pro **BFS**, **DFS**, **Dijkstrův**, **Kruskalův** a **Borůvkův** algoritmus.

### Vizualizace a grafický editor (`app/static/js/graph_visualizer.js`)
* **Interaktivní pohled (Pyvis):** Dynamický fyzikální model (zoom, drag & drop uzlů).
* **Statický SVG editor (D3.js):** Umožňuje vyučujícímu ručně doladit pozice uzlů myší, trvale uložit souřadnice do databáze a přegenerovat čistý **PNG obrázek** pro tisk či vložení do testu.
* **Interaktivní přehrávač algoritmů (`/visualize/{id}`):** Krokování průchodu grafem (Play/Pause, Další/Předchozí krok, volba rychlosti animace, barevné zvýraznění právě zkoumaných, přijatých a zamítnutých hran a log kroků).

### Obousměrná podpora formátu `.tg` a exporty pro UIS (`app/exporter.py`)
* **Export do `.tg` (proprietární formát UIS MENDELU):**
  * Zápis uzlů (`u A; u B; ...`) a hran (`h A > B 4 :h1;`).
  * Možnost stáhnout `.tg` soubor pro jednotlivý graf, zkopírovat jeho definici jedním kliknutím do schránky nebo stáhnout hromadný **ZIP archiv** všech vygenerovaných grafů.
* **Import existujícího `.tg` zadání (`POST /import-tg`):**
  * Vyučující může vložit existující `.tg` předpis z UIS a aplikace z něj automaticky sestaví graf, vykreslí jej, spočítá všechny vlastnosti i algoritmy a umožní na něm krokovat průchody.
* **Export výsledků do CSV a JSON:** Tabulkový přehled vygenerovaných otázek a správných odpovědí připravený pro kontrolu a import.

### Databázová persistence v SQLite (`app/database.py`)
* Implementován návrhový vzor **DAO (Data Access Object)** nad vestavěnou databází **SQLite** v režimu WAL (`Write-Ahead Logging`).
* Relační tabulky:
  * `graphs` — metadata grafu, konfigurace, vlastnosti a výsledky algoritmů.
  * `graph_edges` — normalizované hrany grafu umožňující bleskovou rekonstrukci objektu `networkx.Graph`.
  * `graph_positions` — uložené $(x, y)$ souřadnice uzlů z grafického editoru.

### Automatizované testy a CI/CD (`tests/`, `.github/workflows/tests.yml`)
* Sada **42 automatizovaných testů** postavených na frameworku **Pytest** (unit testy algoritmů v `test_solver.py`, testy generátoru v `test_generator.py` a integrační testy REST API v `test_api.py`).
* Testy běží nad izolovanou testovací databází (`TESTING=1`), takže neovlivňují produkční data.
* Součástí repozitáře je **GitHub Actions CI/CD pipeline**, která spouští testy při každém `push` nebo `pull_request`.

---

## 3. Architektura a struktura projektu

```text
.
├── app/
│   ├── main.py                  # Vstupní bod FastAPI aplikace, routování a controller logika
│   ├── database.py              # DAO vrstva pro SQLite (graphs, graph_edges, graph_positions)
│   ├── generator.py             # Generátor grafů nad knihovnou NetworkX
│   ├── solver.py                # Výpočet vlastností grafu, algoritmy a krokování pro vizualizér
│   ├── exporter.py              # Export do .tg, CSV, JSON a parser vstupního .tg formátu
│   ├── models.py                # Pydantic schémata pro validaci vstupů a konfigurace
│   ├── templates/               # Jinja2 HTML šablony (Bootstrap 5)
│   │   ├── base.html            # Hlavní layout a navigace
│   │   ├── index.html           # Domovská stránka
│   │   ├── generate.html        # Formulář generátoru + import .tg zadání
│   │   ├── result.html          # Detail grafu, výsledky algoritmů, matice sousednosti, .tg kód
│   │   ├── export.html          # Přehled všech zadání, filtrování a hromadný export
│   │   ├── visualize.html       # Interaktivní přehrávač kroků algoritmů
│   │   └── documentation.html   # Teoretická dokumentace algoritmů v aplikaci
│   └── static/
│       ├── css/style.css        # Vlastní styly
│       ├── js/graph_visualizer.js # D3.js/SVG editor a animace průchodu algoritmů
│       └── graphs/              # Vygenerované PNG a HTML soubory (gitignored)
├── tests/                       # Automatizované testy (Pytest)
│   ├── conftest.py              # Nastavení testovacího prostředí (TESTING=1)
│   ├── test_solver.py           # Unit testy grafových algoritmů
│   ├── test_generator.py        # Unit testy generátoru grafů
│   └── test_api.py              # Integrační testy FastAPI endpointů
├── docs/                        # Dokumentace architektury a podklady pro text diplomové práce
├── .github/workflows/tests.yml  # GitHub Actions CI pipeline
├── Dockerfile                   # Definice kontejneru aplikace
├── docker-compose.yml           # Orchestrace kontejneru a persistentních volumes
├── requirements.txt             # Python závislosti
└── pytest.ini                   # Konfigurace Pytestu
```

---

## 4. Jak aplikaci spustit

### Varianta A: Pomocí Dockeru (Doporučeno)

```bash
docker compose up --build -d
```

Aplikace poběží na adrese **http://localhost:8000**.  
Vygenerované obrázky a SQLite databáze jsou namapovány do lokálních složek `app/static/graphs` a `app/data`, takže data zůstanou zachována i po vypnutí kontejneru.

### Varianta B: Lokální spuštění (Python 3.9+)

1. Vytvořte a aktivujte virtuální prostředí:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Nainstalujte závislosti:
   ```bash
   pip install -r requirements.txt
   ```
3. Spusťte server (z kořenového adresáře nebo ze složky `app/`):
   ```bash
   cd app && uvicorn main:app --reload --port 8000
   ```
4. Otevřete v prohlížeči **http://localhost:8000**.

---

## 5. Spuštění automatizovaných testů

```bash
source venv/bin/activate
TESTING=1 pytest tests/ -v
```
