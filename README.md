Il progetto è generato con l'utilizzo di vari LLM.

# Osservatorio Gestionali Italiani

Raccolta di dati sui software gestionali usati in Italia: prodotti, software house, ricavi, feature, dipendenza hardware e lock-in. I dati stanno in un database SQLite, vengono prodotti da bundle JSON con fonti verificabili e si consultano tramite una dashboard web statica.

## Il catalogo

- 373 prodotti e 320 software house, divisi in 10 macro-settori.
- Perimetro: solo software house italiane. I gestionali internazionali distribuiti in Italia da gruppi esteri non sono inclusi.
- Per ogni prodotto: produttore e gruppo, ricavo societario da bilancio, feature, specifiche tecniche, dispositivi hardware, modello commerciale e apertura API.
- I valori economici sono della società produttrice, non del singolo software.

## La dashboard

Un file `web/index.html` senza dipendenze esterne, con cinque viste:

- **Catalogo**: ricerca full-text e filtri per macro-settore, categoria, hardware, lock-in, modello commerciale e API. Vista a schede o a tabella.
- **Mercato**: ricavi per software house e per settore, concentrazione, trasparenza dei listini.
- **Hardware**: dipendenza hardware per settore e i dispositivi fisici ricorrenti (RT/POS, tornelli, timbratrici, ecc.).
- **Lock-in**: fattori di lock-in (normativo, suite, API, hardware) e distribuzione nel catalogo.
- **Metodologia**: criteri di audit e disclaimer.

Per vederla in locale, con solo Python 3:

```bash
python3 scripts/export_web_data.py
python3 -m http.server 8000 --directory web
```

Poi apri `http://127.0.0.1:8000`.

## I 10 macro-settori

| Macro-Settore | Ambiti |
| :--- | :--- |
| Hospitality & Strutture Ricettive | PMS, booking engine, channel manager |
| Ristorazione & Food Service | casse, comande, delivery, HACCP |
| HR, Paghe & Gestione Personale | cedolini, presenze, turni, welfare |
| Retail, Cassa & E-commerce | RT, omnichannel, dealer management |
| Manifattura & Industria 4.0 | MES, QMS, LIMS, Industrial IoT |
| Logistica, Magazzino & Flotte | WMS, TMS, spedizioni, tracking |
| Field Service, Cantieri & Manutenzione | commesse edili, computi, CMMS |
| Pubblica Amministrazione & Utility | tributi, TARI, idrico, PagoPA |
| Professioni, Salute, Sport & No-Profit | studi legali e medici, palestre, ASD, scuole |
| ERP, Finanza & Controllo | ERP, contabilità, fatturazione SDI, bilancio |

## Uso del database

Serve Python 3.11+ (solo libreria standard).

```bash
python3 scripts/init_db.py
python3 scripts/validate_inbox.py examples/vendor-example.json
python3 scripts/import_inbox.py examples/vendor-example.json
python3 scripts/query_examples.py
```

Struttura:

- `data/catalog.sqlite` — database relazionale con ricerca FTS5, ricostruibile dai bundle.
- `data/inbox/YYYY-MM/` — bundle JSON di ricerca, con URL fonte e data.
- `web/index.html`, `web/catalog-data.js` — dashboard e dati esportati.
- `scripts/` — init, import, validazione, export e report.
- `schemas/` — schemi SQL e JSON dei bundle.
- `docs/` — modello dati, playbook di ricerca, note su fonti e sicurezza.

## Contribuire

Per segnalare un gestionale mancante apri una [Issue](https://github.com/iatecoding/mappa-gestionali/issues) con nome del software, produttore, sito e categoria.

Per un contributo strutturato crea un bundle JSON in `data/inbox/YYYY-MM/` conforme a `schemas/research-bundle.schema.json`, validalo con `python3 scripts/validate_inbox.py <file>` e apri una Pull Request.

## Licenza

- Codice: [MIT](LICENSE).
- Dati e catalogo: [CC0 1.0](LICENSE-DATA), pubblico dominio.
- I marchi e i nomi aziendali citati appartengono ai rispettivi titolari e sono usati solo in funzione descrittiva. Dettagli in [NOTICE](NOTICE).
- I dati provengono da fonti pubbliche (siti ufficiali, documentazione tecnica, bilanci e registri camerali). Per correzioni o rimozioni apri una Issue.
