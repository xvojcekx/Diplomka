# Webová aplikace pro generování úloh z teorie grafů

**Diplomová práce — PEF MENDELU v Brně**  
**Autor:** Bc. Vojtěch Střílka  
**Vedoucí práce:** Ing. Pavel Haluza, Ph.D.

---

## 1. K čemu aplikace slouží

Tato webová aplikace slouží k **automatizovanému generování, analýze, interaktivní vizualizaci, přípravě tiskových písemek se slovním zadáním a exportu grafových úloh** pro výuku předmětu *Teorie grafů* na Provozně ekonomické fakultě Mendelovy univerzity v Brně (PEF MENDELU).

Řeší klíčový problém přípravy testových a cvičebních zadání: vyučující nemusí ručně vymýšlet grafy, kreslit jejich obrázky, vymýšlet kontextová slovní zadání a ručně přepočítávat mezivýsledky pro každou variantu testu. Aplikace na základě zvolených parametrů nebo didaktických předvoleb vygeneruje požadovaný počet unikátních grafů, automaticky pro ně vypočítá správná řešení referenčních algoritmů, sestaví tiskový pracovní list písemky a připraví podklady pro přímý import do **Univerzitního informačního systému (UIS MENDELU)**.

---

## 2. Přehled funkcionalit

### Výuka — demo a didaktické předvolby (`app/scenarios.py`, `/teaching`, `/exam/{id}`)
* **Didaktické předvolby na jedno kliknutí (`/teaching`):** Rychlé vygenerování grafu se zaručenými pedagogickými vlastnostmi pro sedm typových úloh:
  1. **Nejkratší cesta (Dijkstrův algoritmus)** — logistický rozvoz zásilek mezi městy.
  2. **Trasa s povinnou mezizastávkou bez opakování hran** — nalezení nejkratšího hranově disjunktního sledu $S \to M \to T$ s automatickým výběrem mezizastávky mimo přímou nejkratší cestu a vyčíslením časového zdržení.
  3. **Minimální kostra sítě (Kruskalův algoritmus)** — návrh páteřní optické sítě s volitelnou garancí unikátních vah hran (zaručeně jednoznačná kostra).
  4. **Záporné ohodnocení hran (Bellmanův-Fordův algoritmus)** — finanční arbitráž se zápornou hranou bez záporného cyklu (didaktická past demonstrující selhání hladového přístupu Dijkstrova algoritmu).
  5. **Zranitelnost sítě (Mosty a artikulace)** — kritická infrastruktura se zaručeným mostem a artikulačními body včetně automatického návrhu záložní linky.
  6. **Harmonogram projektu (Topologické řazení DAG)** — projektové řízení s výpočtem vstupních stupňů $\deg^-(v)$ pro Kahnův algoritmus.
  7. **Přepravní kapacita potrubní sítě (Max-Flow / Min-Cut)** — Fordův-Fulkersonův (Edmondsův-Karpův) algoritmus s rozkladem vrcholů minimálního řezu $(S, T)$.
* **Tiskové pracovní listy písemek (`/exam/{id}`):**
  * **Režim pro studenta:** Záhlaví písemky (jméno, skupina, datum, ID varianty, seed), kontextové slovní zadání, obrázek grafu se sjednoceným označením uzlů `A (0), B (1)...`, otázky, **předtištěná tabulka pro ruční výpočet** (dle typu algoritmu) a linkovaný prostor pro zápis postupu.
  * **Autorské řešení pro vyučujícího:** Přepnutí jedním tlačítkem zobrazí kompletní vyřešenou tabulku vzdáleností $d(v)$ a předchůdců $p(v)$, rozhodovací tabulku všech hran u Kruskala (*Zařazena / Zamítnuta — tvoří cyklus*), stupně uzlů či toky na hranách.
  * **Interaktivní přepočet nad existujícím grafem:** Vyučující může přímo v záhlaví písemky změnit typ scénáře nebo přepnout výchozí uzel (*Start*), *Mezizastávku* a *Cíl*, případně jedním klikem vygenerovat novou náhodnou variantu.

### Konfigurovatelný generátor grafů (`app/generator.py`, `/generate`)
* **Dávkové generování (Batching):** Možnost vygenerovat 1 až 50 grafů najednou.
* **Dva režimy zadávání:** Přesný počet uzlů/hran nebo náhodný interval `[min, max]`.
* **Strukturální a didaktické vlastnosti:**
  * Orientované (`DiGraph`) i neorientované (`Graph`) grafy.
  * Ohodnocené hrany s nastavitelným rozsahem vah `[weight_min, weight_max]` i neohodnocené grafy.
  * Zaručeně souvislé grafy — u orientovaných grafů generátor konstruuje dopřednou orientovanou kostru (arborescenci) z uzlu `A (0)` do všech ostatních uzlů, aby byla vždy zaručena dosažitelnost cílového uzlu.
  * Acyklické grafy — orientované acyklické grafy (**DAG**) a neorientované **stromy**.
  * **Bipartitní** grafy.
  * **Didaktické přepínače:** *Unikátní váhy hran* (`unique_weights`), *Záporná hrana bez záporného cyklu* (`allow_negative_edge`), *Garantovaný most a artikulace* (`force_bridge`).
* **Štítkování a organizace (`tag`):** Každému grafu či dávce lze přiřadit vlastní štítek (např. `Cvičení 3`, `Písemka A`) a podle něj grafy filtrovat i hromadně exportovat.
* **Reprodukovatelnost:** Podpora `seed` parametru (stejný seed vygeneruje identický graf).

### Výpočetní jádro a algoritmy (`app/solver.py`)
* **Základní invarianty a vlastnosti grafu:** Počet uzlů a hran, orientovanost, souvislost, hustota grafu, průměr grafu (diameter), stupňová posloupnost, extrémy stupňů uzlů a vah hran.
* **Automatické řešení úloh:**
  * **Dijkstrův algoritmus** — nejkratší cesta a její délka (s možností interaktivního přepočtu pro libovolnou dvojici uzlů).
  * **Bellmanův-Fordův algoritmus** — nejkratší cesty i pro grafy se zápornými vahami hran včetně detekce záporných cyklů.
  * **Kruskalův algoritmus** — minimální kostra grafu (MST) a její celková váha.
  * **Edmonds-Karp / Ford-Fulkerson** — maximální tok v síti ze zdroje do spotřebiče a rozklad uzlů/hran tvořících **minimální řez**.
  * **Barvení grafu (Welsh-Powell / Greedy)** — obarvení uzlů, rozdělení do barevných tříd a horní odhad chromatického čísla $\chi(G)$.
  * **Eulerovské grafy** — ověření existence Eulerovského tahu a Eulerovské kružnice včetně vypsání posloupnosti hran.
  * **Hamiltonovské grafy** — exaktní vyhledání Hamiltonovské cesty a Hamiltonovské kružnice (backtracking).
  * **Analýza souvislosti a kritických prvků** — silně souvislé komponenty (**SCC** — Tarjanův algoritmus) pro orientované grafy, **artikulace** (kritické uzly) a **mosty** (kritické hrany) pro neorientované grafy.
  * **Topologické třídění** — ověření acykličnosti a výpis topologického uspořádání pro orientované grafy.
  * **Test bipartitnosti** — rozdělení uzlů do dvou disjunktních množin $U$ a $V$.
* **Krokování algoritmů pro výuku:** Detailní generování jednotlivých kroků pro **BFS**, **DFS**, **Dijkstrův**, **Bellmanův-Fordův**, **Kruskalův** a **Borůvkův** algoritmus.

### Automatický validátor studentských řešení — Grader v2 (`app/grader.py`)
* Řeší klíčový didaktický problém **víceznačných úloh**, kde má jeden graf více různých, ale stejně správných řešení:
  * **Validace minimální kostry (MST):** Uzná libovolnou podmnožinu hran (např. `h1, h3, h5` nebo `u0-u1, u1-u2`), která je souvislá, bez cyklů a dosahuje minimální možné váhy.
  * **Validace nejkratší cesty:** Uzná libovolnou platnou cestu ze zdroje do cíle, jejíž součet vah se rovná optimální nejkratší vzdálenosti.
  * **Validace topologického uspořádání:** Ověří, že pro každou orientovanou hranu $(u, v)$ se uzel $u$ nachází v odpovědi studenta před uzlem $v$.
* Při neočekávaném nebo nečitelném formátu odpovědi automaticky nastaví příznak `manual_review: True` pro upozornění vyučujícího.

### Vizualizace a grafický editor (`app/static/js/graph_visualizer.js`)
* **Sjednocené duální popisky uzlů (`A (0)`, `B (1)`, …):** Ve statickém PNG, interaktivním Pyvis modelu i v SVG krokovacím plátně jsou uzly označeny současně písmenem i číselným indexem.
* **Interaktivní pohled (Pyvis):** Dynamický fyzikální model (zoom, drag & drop uzlů).
* **Statický SVG editor:** Umožňuje vyučujícímu ručně doladit pozice uzlů myší, trvale uložit souřadnice do databáze a přegenerovat čistý **PNG obrázek** pro tisk či vložení do testu.
* **Interaktivní přehrávač algoritmů (`/visualize/{id}`):** Krokování průchodu grafem (Play/Pause, Další/Předchozí krok, volba rychlosti animace, barevné zvýraznění právě zkoumaných, přijatých a zamítnutých hran a log kroků).

### Obousměrná podpora formátu `.tg` a exporty pro UIS (`app/exporter.py`)
* **Export do `.tg` (formát používaný v předmětu Teorie grafů na PEF MENDELU):**
  * Zápis uzlů (`u A; u B; ...`) a hran (`h A > B 4 :h1;`).
  * Možnost stáhnout `.tg` soubor pro jednotlivý graf, zkopírovat jeho definici jedním kliknutím do schránky nebo stáhnout hromadný **ZIP archiv** vygenerovaných grafů (včetně filtrování podle štítku `tag`).
* **Import existujícího `.tg` zadání (`POST /import-tg`):**
  * Vyučující může vložit existující `.tg` předpis a aplikace z něj automaticky sestaví graf, vykreslí jej, spočítá všechny vlastnosti i algoritmy a umožní z něj vygenerovat i tiskovou písemku (`/exam/{id}`).
* **Export výsledků do CSV a JSON:** Tabulkový přehled vygenerovaných otázek a správných odpovědí.

### Databázová persistence v SQLite (`app/database.py`)
* Implementován návrhový vzor **DAO (Data Access Object)** nad vestavěnou databází **SQLite** v režimu WAL (`Write-Ahead Logging`) s automatickou migrací schématu při startu.
* Relační tabulky:
  * `graphs` — metadata grafu, konfigurace, vlastnosti, výsledky algoritmů a uživatelský štítek (`tag`).
  * `graph_edges` — normalizované hrany grafu umožňující rychlou rekonstrukci objektu `networkx.Graph`.
  * `graph_positions` — uložené $(x, y)$ souřadnice uzlů z grafického editoru.

### Automatizované testy a CI/CD (`tests/`, `.github/workflows/tests.yml`)
* Sada **66 automatizovaných testů** postavených na frameworku **Pytest** (unit testy algoritmů a validátoru v `test_solver.py`, testy generátoru a didaktických voleb v `test_generator.py` a integrační testy REST API, výukových předvoleb a písemek v `test_api.py`).
* Testy běží nad izolovanou testovací databází (`TESTING=1`), takže neovlivňují produkční data.
* Součástí repozitáře je **GitHub Actions CI/CD pipeline**, která spouští testy při každém `push` nebo `pull_request`.

---

## 3. Architektura a struktura projektu

```text
.
├── app/
│   ├── main.py                  # Vstupní bod FastAPI aplikace, routování a controller logika
│   ├── database.py              # DAO vrstva pro SQLite (graphs, graph_edges, graph_positions)
│   ├── generator.py             # Generátor grafů a didaktických garancí nad knihovnou NetworkX
│   ├── solver.py                # Výpočet vlastností grafu, algoritmy a krokování pro vizualizér
│   ├── scenarios.py             # Generátor slovních zadání, předtištěných tabulek a klíčů písemek
│   ├── grader.py                # Automatický validátor studentských odpovědí (Grader v2)
│   ├── exporter.py              # Export do .tg, CSV, JSON a parser vstupního .tg formátu
│   ├── models.py                # Pydantic schémata pro validaci vstupů a konfigurace
│   ├── templates/               # Jinja2 HTML šablony (Bootstrap 5)
│   │   ├── base.html            # Hlavní layout a navigace
│   │   ├── index.html           # Domovská stránka
│   │   ├── teaching.html        # Výuka — demo (didaktické předvolby na jedno kliknutí)
│   │   ├── exam.html            # Tiskový pracovní list písemky (verze pro studenta i učitele)
│   │   ├── generate.html        # Formulář ručního generátoru + import .tg zadání
│   │   ├── result.html          # Detail grafu, výsledky algoritmů, matice sousednosti, .tg kód
│   │   ├── export.html          # Přehled všech zadání, filtrování podle štítků a hromadný export
│   │   ├── visualize.html       # Interaktivní přehrávač kroků algoritmů a editor pozic
│   │   └── documentation.html   # Teoretická dokumentace algoritmů v aplikaci
│   └── static/
│       ├── css/style.css        # Vlastní styly
│       ├── js/graph_visualizer.js # SVG editor a animace průchodu algoritmů
│       └── graphs/              # Vygenerované PNG a HTML soubory (gitignored)
├── tests/                       # Automatizované testy (Pytest — 66 testů)
│   ├── conftest.py              # Nastavení testovacího prostředí (TESTING=1)
│   ├── test_solver.py           # Unit testy grafových algoritmů a validátoru
│   ├── test_generator.py        # Unit testy generátoru grafů a didaktických voleb
│   ├── test_api.py              # Integrační testy FastAPI endpointů, výuky a písemek
│   └── test_independent_verification.py  # Nezávislé ověření algoritmů hrubou silou a vlastní implementací
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
