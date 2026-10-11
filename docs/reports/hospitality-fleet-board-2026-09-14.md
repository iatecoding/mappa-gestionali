# Hospitality fleet board

Avvio: 14 settembre 2026. Tutti gli agenti hanno lavorato in sola lettura; nessun subagent ha modificato la codebase del prodotto o il catalogo.

## Fleet eseguite

| Agente | Lane | Lock | Stato | Consegna |
|---|---|---|---|---|
| Ampere | UX / competitor | `UX-COMP-01` | completata | deltas visuali, IA, front desk e competitor |
| Nietzsche | PMS domain | `DOMAIN-PMS-01` | completata | modello dati, capability e gap PMS |
| Leibniz | technical limits | `TECH-LIMITS-01` | completata | SQLite, API, security, retention, jobs e performance |
| Bohr | visual QA | `VISUAL-QA-01` | completata | screenshot 390/1440, overflow, density e fix order |
| Herschel | QA / pilot | `QA-PILOT-01` | completata | coverage, no-go, scenari di campo e soglie |
| McClintock | BI / source quality | `BI-SOURCES-01` | completata | catalogo, freshness, deduplica e backlog research |

I risultati sono stati integrati in [hospitality-product-audit-2026-09-14.md](hospitality-product-audit-2026-09-14.md). Le evidenze visuali sono in [`data/reports/hospitality-audit-2026-09-14/evidence/`](../../data/reports/hospitality-audit-2026-09-14/evidence/).

## Lock per la prossima wave

### Ricerca BI

Queste lane non devono lavorare sulla stessa URL o sullo stesso candidate:

- `BI-SOURCES-01-REG`: Alloggiati, Istat, Garante, Agenzia delle Entrate, tassa comunale;
- `BI-SOURCES-01-PMS`: PMS e workflow front office;
- `BI-SOURCES-01-DIST`: channel manager, booking engine e API;
- `BI-SOURCES-01-VERT`: camping, agriturismo, spa, F&B/POS, marina, attività;
- `BI-SOURCES-01-TECH`: API, sicurezza, resilienza, retention, DPA e offline;
- `BI-SOURCES-01-FIN`: identità legale, prezzi, fatturato aziendale e metriche finanziarie;
- `BI-SOURCES-01-QA`: deduplica, freshness e validazione soltanto.

Regole obbligatorie:

1. Riservare la URL canonica prima di visitarla con [`scripts/research_registry.py`](../../scripts/research_registry.py).
2. Riutilizzare una cache `ready`; non rifetchare una risorsa `busy`.
3. Un bundle JSON per agent/lane; nessuna scrittura diretta sul database da parte dei ricercatori.
4. Una sola persona/processo di import e cura seriale.
5. Ogni claim deve avere source, data di recupero, estratto, tipo di evidenza e livello di confidenza.
6. “Non osservato” non deve diventare “non supportato”.

Priorità iniziali: fonti normative primarie, API/rate-limit/webhook dei connettori, riconciliazione dei 24 candidate `researching`, deduplica delle URL e refresh delle 246 cache oltre data.

### Scrittura codebase

Quando si passerà dall’audit all’implementazione, assegnare ownership disgiunta:

| Lock | Scope di scrittura |
|---|---|
| `WRITE-UI` | templates, componenti, CSS Hospitality e copy |
| `WRITE-DOMAIN` | migrazioni, invarianti e servizi domain PMS |
| `WRITE-INTEGRATIONS` | provider, API, outbox, webhook e retry |
| `WRITE-QA` | test, fixture, benchmark, screenshot e release gate |

Nessun agent modifica file fuori dal proprio scope. Il working tree corrente è dirty: prima di qualsiasi wave di coding va scelto un commit candidato pulito oppure registrato l’elenco delle modifiche preesistenti.
