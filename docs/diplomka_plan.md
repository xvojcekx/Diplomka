# Diplomová práce — Rozbor zadání a stav realizace

**Název:** Webová aplikace na generování grafů pro potřeby výuky teorie grafů  
**Autor:** Bc. Vojtěch Střílka  
**Vedoucí:** Ing. Pavel Haluza, Ph.D.  
**Rozsah:** 2,5–4 AA (~65–100 normostran)

---

## 1. Mapování bodů zadání na současný stav projektu

| # | Bod zadání | Stav implementace v aplikaci | Stav v textu diplomové práce (`diplomka_uvod_teorie.docx`) |
|---|-----------|------------------------------|-----------------------------------------------------------|
| 1 | **Nastudovat** backendové technologie, vizualizaci (interaktivní + statickou), responzivní UI, kontejnerizaci | ✅ Hotovo (FastAPI, NetworkX, Pyvis, SVG/JS, Matplotlib, Bootstrap 5, Docker) | ✅ Hotovo — Kapitola 2 (Teoretická východiska) |
| 2 | **Formulovat požadavky** na funkcionalitu ve spolupráci s vyučujícími | ✅ Hotovo (funkční F1–F16, nefunkční N1–N7, případy užití UC1–UC8) | ✅ Hotovo — Kapitola 3 (Analýza požadavků) |
| 3 | **Navrhnout architekturu**, uživatelské rozhraní a **datovou strukturu** | ✅ Hotovo (4vrstvá architektura, SQLite DAO se 3 tabulkami + štítky `tag`, 9 šablon včetně `/teaching` a `/exam/{id}`) | ✅ Hotovo — Kapitola 4 (Návrh řešení) |
| 4 | **Implementovat** webovou aplikaci s Docker kontejnerizací | ✅ Hotovo (`generator.py`, `solver.py`, `scenarios.py`, `grader.py`, `exporter.py`, `database.py`, `Dockerfile`, `docker-compose.yml`) | ✅ Hotovo — Kapitola 5 (Implementace) |
| 5 | **Ověřit funkčnost** standardními testy | ✅ Hotovo (**68 automatizovaných Pytest testů** + GitHub Actions CI pipeline) | ✅ Hotovo — Kapitola 6 (hodnocení vyučujícím čeká na doplnění) |
| 6 | **Zhodnotit** navržené řešení | ✅ Podklady kompletní | ✅ Hotovo — Kapitola 6 a Závěr |

---

## 2. Přehled stránek aplikace (pro kapitolu Návrh a Implementace UI)

Aplikace obsahuje **8 uživatelských obrazovek** postavených na společné šabloně `base.html`:

1. **Domovská stránka (`/`, `index.html`)** — rozcestník pro vyučujícího a statistika databáze.
2. **Výuka — demo (`/teaching`, `teaching.html`)** — didaktické předvolby na jedno kliknutí (Dijkstra, Trasa s mezizastávkou bez opakování hran, Kruskal MST s unikátními vahami, Bellman-Ford se zápornou hranou bez záporného cyklu, Mosty a artikulace, Topologické řazení DAG, Max-Flow/Min-Cut).
3. **Tiskový pracovní list písemky (`/exam/{id}`, `exam.html`)** — kontextové slovní zadání, obrázek grafu se sjednocenými popisky `A (0)`, předtištěná tabulka pro ruční výpočet studenta, přepínač na kompletní autorské řešení pro vyučujícího a horní lišta pro změnu scénáře či uzlů Start/Mezizastávka/Cíl.
4. **Ruční generátor a import `.tg` (`/generate`, `generate.html`)** — dávkové generování 1–50 grafů, strukturální a didaktické přepínače (`unique_weights`, `allow_negative_edge`, `force_bridge`), štítkování (`tag`) a obousměrný import `.tg`.
5. **Detail grafu a řešení (`/result/{id}`, `result.html`)** — interaktivní Pyvis pohled, matice sousednosti, seznam hran, výsledky 10 algoritmů, export `.tg` a sémantický validátor studentských odpovědí (Grader v2).
6. **Krokování algoritmů a editor rozložení (`/visualize/{id}`, `visualize.html`)** — SVG plátno s animací kroků (BFS, DFS, Dijkstra, Bellman-Ford, Kruskal, Borůvka) a ukládáním ručně upravených pozic uzlů do SQLite a PNG.
7. **Přehled a export zadání (`/export`, `export.html`)** — správa uložených grafů, filtrování podle štítků (`tag`), přímé prokliky na tisk písemky a hromadný export (`.tg` ZIP, CSV, JSON).
8. **Dokumentace algoritmů (`/docs-algorithms`, `documentation.html`)** — teoretický přehled algoritmů, složitostí a pseudokódů.
