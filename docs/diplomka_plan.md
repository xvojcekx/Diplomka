# Diplomová práce — Rozbor zadání a plán

**Název:** Webová aplikace pro generování úloh z teorie grafů  
**Autor:** Bc. Vojtěch Střílka  
**Vedoucí:** Ing. Pavel Haluza, Ph.D.  
**Rozsah:** 2,5–4 AA (~65–100 normostran)

---

## 1. Mapování zadání na současný stav aplikace

| # | Bod zadání | Současný stav | Co chybí |
|---|-----------|--------------|----------|
| 1 | **Nastudovat** backendové technologie, vizualizaci (interaktivní + statickou), responzivní UI, kontejnerizaci | ✅ Implementováno (FastAPI, NetworkX, Pyvis, D3.js, Matplotlib, Bootstrap, Docker) | 📝 Teoretická kapitola v textu DP — formální rešerše |
| 2 | **Formulovat požadavky** na funkcionalitu ve spolupráci s vyučujícími | ⚠️ Částečně — požadavky byly řešeny průběžně | 📝 Formalizovat jako kapitolu "Analýza požadavků" (use-case diagram, tabulka funkčních/nefunkčních požadavků) |
| 3 | **Navrhnout architekturu**, uživatelské rozhraní a **datovou strukturu** | ⚠️ Architektura existuje v kódu, ale není dokumentovaná; **chybí databáze** (data jsou in-memory) | 🔴 **Wireframy** (Figma), architektonický diagram, ER diagram pro SQLite |
| 4 | **Implementovat** webovou aplikaci s Docker kontejnerizací | ✅ Funkční (FastAPI + Dockerfile + docker-compose) | ⚠️ Chybí SQLite persistence, robustnější testy |
| 5 | **Ověřit funkčnost** standardními testy | 🔴 Chybí | 🔴 **Pytest testy** (unit + integrační), validace algoritmů |
| 6 | **Zhodnotit** navržené řešení | 🔴 Chybí | 📝 Kapitola v textu DP |

---

## 2. Co musíš nastudovat (Bod 1 zadání)

Zadání explicitně říká: *„Nastudujte problematiku backendových technologií, technologií pro interaktivní a statickou vizualizaci dat v prohlížeči, nástroje tvořící responzivní uživatelské rozhraní a principy kontejnerizace."*

### 2.1 Backendové technologie
| Téma | Zdroj | Poznámka |
|------|-------|----------|
| **FastAPI** — asynchronní framework | LATHKAR, M. (2023) *High-Performance Web Apps with FastAPI* — **povinná literatura** | Kapitoly o routování, Pydantic validaci, middleware |
| **NetworkX** — grafové algoritmy | HAGBERG et al. (2008) — **povinná literatura** | Zaměř se na API pro generování grafů, BFS/DFS, Dijkstra, Kruskal |
| **Python datové struktury** pro grafy | FARRELLY & MUTOMBO (2024) *Modern Graph Theory Algorithms with Python* — **povinná literatura** | Matice sousednosti, seznamy sousedů, implementace algoritmů |

### 2.2 Vizualizace dat v prohlížeči
| Téma | Zdroj | Poznámka |
|------|-------|----------|
| **D3.js** — interaktivní vizualizace | [d3js.org](https://d3js.org) + Murray, S. (2017) *Interactive Data Visualization for the Web* | Force-directed layout, SVG manipulace |
| **Pyvis** — síťové grafy v HTML | [pyvis.readthedocs.io](https://pyvis.readthedocs.io) | Jak generujeme interaktivní HTML soubory |
| **Matplotlib** — statické vizualizace | [matplotlib.org](https://matplotlib.org) | Serverový rendering (Agg backend), export PNG |
| **SVG vs Canvas** — porovnání přístupů | MDN Web Docs | Pro rešerši — proč jsme zvolili SVG |

### 2.3 Responzivní uživatelské rozhraní
| Téma | Zdroj | Poznámka |
|------|-------|----------|
| **Bootstrap 5** — komponentový framework | [getbootstrap.com](https://getbootstrap.com) | Grid systém, responsivita, komponenty |
| **Jinja2** — šablonovací engine | [jinja.palletsprojects.com](https://jinja.palletsprojects.com) | Dědičnost šablon, filtry, makra |
| **UX principy** pro výukové aplikace | Nielsen, J. (1994) *10 Usability Heuristics* | Pro kapitolu o hodnocení UI |

### 2.4 Kontejnerizace
| Téma | Zdroj | Poznámka |
|------|-------|----------|
| **Docker** — základní principy | Docker official docs + Stoneman, K. (2021) *Learn Docker in a Month of Lunches* | Image, kontejner, Dockerfile, docker-compose |
| **Docker Compose** — multi-kontejnerové řešení | [docs.docker.com/compose](https://docs.docker.com/compose) | Orchestrace služeb |

### 2.5 Automatické hodnocení (Bod 4 literatury)
| Téma | Zdroj | Poznámka |
|------|-------|----------|
| **Automatické hodnocení grafových úloh** | XIANG et al. (2024) — **povinná literatura** | Grafová sémantická podobnost, inspirace pro validaci řešení |

---

## 3. Stránky aplikace — přehled pro wireframy

Aplikace aktuálně obsahuje **7 stránek**. Pro wireframy (doporučuji **Figma** — je zdarma a nejpoužívanější) navrhuji toto rozvržení:

### Stránka 1: Domovská stránka (`/`)
- Hero sekce s názvem aplikace a logem MENDELU
- Rychlé navigační karty (Generovat, Přehled, Vizualizér, Dokumentace)
- Shrnutí posledních vygenerovaných grafů

### Stránka 2: Generátor (`/generate`)
- Formulář s přepínačem (Náhodné rozmezí / Přesný počet)
- Parametry: uzly, hrany, typ grafu (souvislý, bipartitní, DAG…), váhy
- Tlačítko "Generovat" + loading indikátor

### Stránka 3: Detail výsledku (`/result/{id}`)
- Záložky: Interaktivní pohled | Statický editor
- Podpůrné statistiky (stupňová sekvence)
- Vlastnosti grafu + Konfigurace (dvousloupcový layout)
- Statistiky grafu (max/min stupně, max/min váhy)
- Výsledky algoritmů (Dijkstra, MST, topologické třídění, bipartitnost)
- Matice sousednosti (s labely u0, u1…)
- Seznam hran (h1, h2…)

### Stránka 4: Přehled všech zadání (`/export`)
- Tabulka/kartový seznam vygenerovaných grafů
- Náhledy (thumbnail PNG)
- Akce: Detail, Export CSV, Export .tg, Smazat

### Stránka 5: Vizualizér algoritmů (`/visualize/{id}`)
- Interaktivní graf s animací kroků algoritmů
- Výběr počátečního a cílového uzlu
- Krokování algoritmů (BFS, DFS, Dijkstra, Kruskal, Borůvka)

### Stránka 6: Dokumentace (`/docs-algorithms`)
- Popis všech implementovaných algoritmů
- Matematické definice, pseudokód, vizuální příklady
- Rozdělení do sekcí (prohledávání, nejkratší cesty, kostry…)

### Stránka 7: Base layout (`base.html`)
- Navbar (logo MENDELU, navigace, aktivní stav)
- Footer (verze, copyright)
- Responzivní breakpointy

---

## 4. Kritické úkoly pro splnění zadání

### 🔴 Priorita VYSOKÁ (povinné pro obhajobu)
1. **SQLite databáze** — nahradit in-memory `graphs_store` trvalým úložištěm (bod 3 zadání — „datová struktura")
2. **Pytest testy** — unit testy pro solver, integrační testy pro API (bod 5 zadání)
3. **Wireframy ve Figmě** — formální návrh UI pro text diplomky (bod 3 zadání)

### 🟡 Priorita STŘEDNÍ
4. **Architektonický diagram** — blokové schéma modulů (generátor → solver → vizualizér → exportér)
5. **ER diagram** — schéma SQLite tabulek
6. **Use-case diagram** — interakce učitele s aplikací

### 🟢 Priorita NÍZKÁ (nice-to-have)
7. Vylepšení UX/UI na základě zpětné vazby od vyučujícího
8. Rozšíření exportu (víc formátů, hromadný export)

---

## 5. Doporučení pro wireframy — Figma

> [!TIP]
> **Figma** ([figma.com](https://www.figma.com)) je v současnosti nejpoužívanější nástroj na prototypování UI. Je zdarma pro jednotlivce, běží v prohlížeči a výstupy se dají přímo vložit do diplomové práce jako obrázky.

### Jak začít:
1. Založ si účet na [figma.com](https://www.figma.com)
2. Vytvoř nový soubor „DP — Wireframy"
3. Pro každou stránku (viz sekce 3) vytvoř jeden **Frame** (Desktop 1440×900)
4. Použij šedé obdélníky pro obsah, čáry pro tabulky — čistý wireframe styl
5. Exportuj jako PNG a vlož do textu DP do kapitoly „Návrh uživatelského rozhraní"

### Alternativy k Figmě:
| Nástroj | Výhoda | Nevýhoda |
|---------|--------|----------|
| **Figma** | Nejrozšířenější, zdarma, kolaborace | Nutný internet |
| **Balsamiq** | Rychlé lo-fi wireframy | Placený |
| **draw.io / diagrams.net** | Zdarma, offline | Méně vhodný pro UI |
| **Excalidraw** | Skicovitý styl, zdarma | Omezené komponenty |
