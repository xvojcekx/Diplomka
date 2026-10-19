# Studijní materiály a klíčové koncepty pro diplomovou práci

Tento dokument slouží jako tvůj hlavní tahák a průvodce technologiemi, které byly použity v tvé webové aplikaci pro teorii grafů. Obsahuje vysvětlení klíčových konceptů (Key Concepts) a terminologie, kterou bys měl znát k obhajobě a k napsání teoretické části práce.

---

## 1. Backendové technologie

Tato sekce se zaměřuje na to, jak aplikace funguje "pod kapotou" na serveru.

### FastAPI
FastAPI je moderní a rychlý webový framework pro Python sloužící k tvorbě API.
*   **Key Concept: Asynchronní programování (async/await):** Umožňuje serveru zpracovávat další požadavky, zatímco čeká na dokončení jiných úloh (např. čtení z databáze nebo generování složitého grafu), což extrémně zvyšuje propustnost aplikace.
*   **Key Concept: Routování (Endpoints):** Definování URL adres (např. `/generate` nebo `/api/graph/{id}`), na které může uživatel nebo frontend poslat požadavek. FastAPI je mapuje na konkrétní Python funkce.
*   **Key Concept: Pydantic validace:** V naší aplikaci to reprezentují modely jako `GraphConfig`. Pydantic automaticky kontroluje (validuje), zda data od uživatele mají správný typ (např. že `node_count` je číslo mezi 3 a 500). Pokud ne, automaticky vrátí uživateli přehlednou chybu.

### NetworkX
Standardní Python knihovna pro tvorbu, manipulaci a studium struktury, dynamiky a funkcí komplexních síťových grafů.
*   **Key Concept: Grafové objekty (`nx.Graph`, `nx.DiGraph`):** Základní stavební kameny pro neorientované a orientované grafy. V naší aplikaci je používáme k uložení vygenerované struktury a spouštění algoritmů nad ní.
*   **Key Concept: Vestavěné algoritmy:** Knihovna obsahuje již implementované algoritmy (např. zjištění souvislosti, výpočet průměru, generátory náhodných grafů), které pod kapotou používáme v modulu `solver.py` a `generator.py`.

### Datové struktury pro grafy
Způsoby, jakými počítač reprezentuje grafy v paměti.
*   **Key Concept: Matice sousednosti (Adjacency Matrix):** 2D pole (tabulka), kde řádky a sloupce reprezentují uzly. Hodnota na pozici `(i, j)` představuje hranu (a její váhu) mezi uzlem `i` a `j`. Výhoda: rychlé zjištění existence hrany. Nevýhoda: plýtvá pamětí u řídkých grafů.
*   **Key Concept: Seznam hran (Edge List):** Jednoduchý seznam propojení, např. `[(0, 1, váha), (1, 2, váha)]`. V naší aplikaci (v databázi a API) jej hodně využíváme pro jeho kompaktnost a snadný převod do JSONu pro frontend (vizualizér D3.js).

---

## 2. Vizualizace dat v prohlížeči

Způsoby, jak grafy reprezentovat graficky tak, aby jim uživatel rozuměl.

### D3.js (Data-Driven Documents)
JavaScriptová knihovna pro manipulaci s dokumenty na základě dat.
*   **Key Concept: Force-directed layout (Silový model):** Fyzikální simulace, která se používá pro rozmístění uzlů grafu. Uzly se chovají jako magnety, které se navzájem odpuzují (aby se nepřekrývaly), zatímco hrany fungují jako pružiny, které spojené uzly přitahují k sobě. Výsledkem je esteticky příjemné rozložení.
*   **Key Concept: Data Binding (Navázání dat):** Základní princip D3.js. Propojíme pole dat (např. seznam uzlů) s HTML/SVG elementy. Když se data změní, D3.js automaticky updatuje vizuální prvky na obrazovce.

### SVG vs Canvas
Dvě hlavní technologie pro kreslení grafiky v prohlížeči.
*   **Key Concept: SVG (Scalable Vector Graphics):** Vykresluje objekty jako HTML tagy (např. `<circle>`, `<line>`). Každý prvek je součástí DOM stromu (Document Object Model).
    *   *Výhoda:* Lze na ně klikat, přidávat CSS styly, animovat. Ideální pro naši aplikaci, kde učitel může s grafy interagovat.
*   **Key Concept: Canvas:** Rastrové plátno, kam se grafika vykresluje pixel po pixelu pomocí JavaScriptu.
    *   *Výhoda:* Extrémně rychlé pro tisíce objektů. *Nevýhoda:* Prvky nejsou v DOMu, hůře se s nimi interaguje (nedá se např. jednoduše navázat "kliknutí na konkrétní uzel"). My používáme SVG právě kvůli interaktivitě.

### Pyvis a Matplotlib
*   **Matplotlib (Server-side rendering):** Používáme ho na backendu k vygenerování statického PNG obrázku (tzv. "Agg backend", který nevyžaduje okno monitoru). Funguje jako "fotoaparát", který graf vyfotí a uloží na disk pro export do UIS.
*   **Pyvis:** Knihovna, která vezme NetworkX graf a vygeneruje hotový HTML soubor s interaktivním zobrazením (používá JS knihovnu vis.js). Slouží jako rychlý a interaktivní náhled pro vyučující.

---

## 3. Responzivní uživatelské rozhraní

Jak zajistit, aby aplikace vypadala dobře na různých zařízeních a byla příjemná na použití.

### Bootstrap 5
Nejpopulárnější CSS framework pro vývoj responzivních webů.
*   **Key Concept: 12-sloupcový Grid System:** Rozděluje šířku stránky na 12 pomyslných sloupců. Pomocí tříd (např. `col-md-6`) určujeme, kolik sloupců má prvek zabrat na určité velikosti obrazovky (md = tablety a větší). Umožňuje snadno přeskládat obsah pro mobily a desktopy.
*   **Key Concept: Předpřipravené komponenty:** Tlačítka, navigační lišty (navbar), karty (cards), modální okna. Nemusíme je psát od nuly v CSS.

### Jinja2
Šablonovací systém pro Python (vestavěný do FastAPI).
*   **Key Concept: Šablonování a dědičnost (Template Inheritance):** Máme jeden hlavní soubor (`base.html`), který obsahuje kostru stránky (menu, patičku, vložení CSS). Ostatní stránky (např. `generate.html`) z něj "dědí" (`{% extends "base.html" %}`) a pouze doplňují svůj specifický obsah do bloku (`{% block content %}`). Zabraňuje to duplikaci kódu.

### UX Principy
*   **Key Concept: Usability Heuristics (Nielsen):** Pravidla pro tvorbu srozumitelného UI. Například "Viditelnost stavu systému" (aplikace ukazuje loading indikátor při generování) nebo "Prevence chyb" (formulář neumožní zadat záporný počet uzlů). Budou se hodit pro kapitolu zhodnocení návrhu aplikace.

---

## 4. Kontejnerizace

Způsob, jak aplikaci sbalit a spustit kdekoliv bez ohledu na to, jaký má uživatel operační systém.

### Docker
*   **Key Concept: Image (Obraz):** Neupravitelná šablona, která obsahuje úplně vše potřebné pro běh aplikace – operační systém (lehký Linux), Python, nainstalované knihovny a samotný kód. Vytváří se podle instrukcí v souboru `Dockerfile`.
*   **Key Concept: Container (Kontejner):** Běžící instance obrazu (Image). Můžeš si ho představit jako izolovanou virtuální pračku, ve které běží jen tvoje aplikace a nevidí zbytek počítače.
*   **Key Concept: Volume (Svazek):** Způsob, jak zachovat data i po smazání kontejneru. Kontejnery jsou "stateless" (zapomínají). V naší aplikaci jsme namapovali adresář `app/data/` do Volume, takže SQLite databáze (záznamy o grafech) zůstane zachována.

### Docker Compose
*   **Key Concept: Orchestrace (docker-compose.yml):** Nástroj pro definování a spouštění aplikací tvořených jedním nebo více kontejnery. Místo vypisování dlouhých příkazů do terminálu definujeme konfiguraci (porty, volumes) do YAML souboru a aplikaci spustíme jedním příkazem `docker compose up`.

---

## 5. Automatické hodnocení a uložení dat (Databáze)

### SQLite
Naše databázová technologie.
*   **Key Concept: ACID:** Zkratka pro vlastnosti databáze zaručující spolehlivost: Atomicita (transakce se provede celá nebo vůbec), Konzistence, Izolace, Trvanlivost (data jsou uložena trvale i po výpadku proudu).
*   **Key Concept: Relační struktura vs. JSON:** V databázi používáme hybridní přístup. Fixní data (hrany, pozice, základní údaje) jsou v relačních tabulkách pro snadné dotazování. Proměnlivá data (konfigurace, výsledky algoritmů, které mohou u každého grafu vypadat jinak) ukládáme jako strukturovaný text (JSON). To dává aplikaci obrovskou flexibilitu do budoucna.

### Validace řešení
*   **Key Concept: Sémantická podobnost:** Při generování úloh (zejména pro UIS) musíme znát správnou odpověď předem (např. délka MST, nejkratší cesta). Naše aplikace (modul `solver.py`) tuto správnou odpověď vypočítá ve stejném kroku, jako generuje graf, a uloží ji do exportu. Tím zajišťujeme, že každé zadání má své ověřené řešení pro automatické opravení studentských testů.
