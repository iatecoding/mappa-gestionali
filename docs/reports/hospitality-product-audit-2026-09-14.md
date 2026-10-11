# Hospitality product audit — gestionale-anagrafica

Snapshot: 14 settembre 2026 · branch `feat/hospitality-verticalization` · HEAD `626f066`

## Executive verdict

`gestionale-anagrafica` oggi è una buona base per un cockpit operativo locale — unità, prenotazioni, presenza, pulizie, pre-check-in, richieste, passaggio consegne e conto manuale — ma non è ancora un PMS Hospitality competitivo end-to-end.

Il problema principale non è una singola feature mancante: è la distanza tra tre prodotti percepiti dall’utente:

1. una dashboard generale ancora orientata a HSE/HR;
2. una Ricettività operativa promettente ma con modelli dati semplificati;
3. un ecosistema PMS, distribuzione, pagamenti e adempimenti che oggi è dichiarato fuori perimetro.

La priorità corretta è prima rendere coerente e affidabile il turno reception–piani, poi estendere il perimetro commerciale e regolatorio. Non va presentato come PMS completo finché non esistono almeno conto/folio, rate, adempimenti italiani e integrazioni con una fonte esterna di disponibilità.

## Evidenza raccolta

Sono state usate quattro linee indipendenti:

- codebase, migrazioni, documentazione e test del prodotto;
- cattura Playwright su 12 route, viewport 1440px e 390px, dataset con arrivi, in-house e camera sporca;
- confronto con documentazione ufficiale di PMS, distribuzione e adempimenti;
- catalogo BI `mappa-gestionali`, con fonti e claim separati.

Risultati tecnici della snapshot:

| Controllo | Risultato | Lettura |
|---|---:|---|
| Route Hospitality catturate | 12 × 2 viewport | tutte HTTP 200 |
| Browser critical flows | 27/27 pass | copertura smoke buona, non sufficiente per un pilot |
| Release gate mirato | 48/48 moduli target pass | gate complessivo ancora `no-go` per card RX-026..041 aperte |
| Suite completa | 375 moduli / 7.748 casi | 1 modulo fallito: `test_scenario_hospitality_soggiorno_dirty` |
| Responsive `workspace/hospitality` | 390px → document width 417px | quattro elementi escono dal viewport |
| Responsive `ricettivita/report` | altezza 8.156px, 8 nodi overflow | report inutilizzabile come strumento di turno su mobile |
| Superficie `app/ricettivita/__init__.py` | 6.508 righe | elevato accoppiamento per ulteriori integrazioni |
| Hospitality inline UI | 19 `style=`, 6 handler inline | CSP e manutenzione ancora compromessi |

Il fallimento della suite non è cosmetico. Il test chiama `elimina_unita(... today="2026-09-15")` mentre l’esecuzione corrente è il 14 settembre e la prenotazione termina il 16: la guardia di dominio rifiuta correttamente la cancellazione, ma il test ignora il risultato e poi pretende la schermata dell’unità eliminata. È una fixture dipendente dall’orologio e un contratto di test incompleto: va resa deterministica prima di usare la suite come gate.

Le schermate sono in [`data/reports/hospitality-audit-2026-09-14/evidence/`](../../data/reports/hospitality-audit-2026-09-14/evidence/), con `metrics.json` come indice misurabile.

## Gap map completa

La lista dettagliata G01–G60 resta nel dossier di revisione del prodotto. Questa tabella la ricompone in workstream, con il giudizio aggiornato dalla verifica visuale e tecnica.

| Workstream | Stato attuale | Cosa manca o va ripensato | Priorità |
|---|---|---|---:|
| Identità e ingresso | parziale | profilo Hospitality esplicito, home “Oggi”, contesto azienda/sede/struttura persistente, onboarding senza dipendenti fittizi | P0 |
| Inventario | parziale | separare tipo/categoria vendibile da unità fisica; prenotazione non assegnata; alternative, waitlist, capienza adulti/bambini/letti/accessibilità; conflitto con recupero | P0 |
| Ospiti e soggiorno | parziale | persone individuali, minori, booker/ospite/pagante, identità verificabile, arrivi parziali, day-use, early/late, room move, estensione e partenza anticipata | P0 |
| Tariffe e condizioni | assente/parziale | rate plan versionati, inclusioni, stagionalità, occupancy supplement, min/max nights, CTA/CTD, stop-sell, no-show, cancellazione, caparra/garanzia | P1 |
| Conto e finanza | parziale | folio completo, righe/extra, split e trasferimenti, crediti/rimborsi/storni, saldo verificabile, sessione cassa, night audit, riconciliazione e incassi aperti | P0 |
| Pagamenti e fiscalità | assente | adapter PSP, webhook idempotenti, payment links, VCC, refund/chargeback, documento fiscale e source-of-truth amministrativo | P1 |
| Housekeeping | parziale | stayover, DND/rifiuto, priorità per arrivo, carico e assegnazione, QC con log; separare “sporco” da “non vendibile” e blocco manutenzione | P0 |
| Manutenzione e servizi | parziale | ciclo guasto → blocco → intervento → verifica → ritorno alla vendita; minibar, lavanderia, lost & found, service request e reclami | P1 |
| Comunicazioni | parziale | inbox/conversazioni, template per evento, consenso, retry, delivery status, escalation e assegnazione al reparto | P1 |
| Pre-check-in | parziale | elenco persone e ruoli, verifica/correzione controllata, dati necessari per il processo; il badge non deve implicare identità verificata o invio normativo | P0 |
| Alloggiati / territorio | assente | Alloggiati Web con ricevute, errori e retry; statistiche Istat; tassa di soggiorno con regole/esenzioni/settlement | P0 |
| Reporting | debole | ADR, RevPAR, pickup, lead time, forecast, netto per canale/commissione, revenue, report di carico housekeeping; report mobile leggibile | P1 |
| Gruppi e segmenti | parziale | rooming list, multi-room, allotment/release/pickup, corporate/agencies, contratti e condizioni | P1 |
| Distribuzione | outbound iCal soltanto | channel manager, mapping, booking engine, disponibilità bidirezionale, stop-sell, rate push, OTA reconciliation | P1 |
| Multi-property | assente/parziale | portfolio, ruoli per struttura, disponibilità/conti/report consolidati, trasferimenti tra proprietà | P1 |
| Verticali adiacenti | assente | F&B/POS e food cost, spa/attività, camping con piazzole/veicoli/accessi, lock/key/access control, property/owner management | P2 |
| Startup e migrazione | parziale | import hospitality, mapping categorie/camere, deduplica ospiti, checklist go-live, rollback e formazione per ruolo | P0 |
| Continuità | da provare | RPO/RTO dichiarati, backup testato, procedura rete assente, coda/retry, modalità degradata/offline, export completo | P1 |
| Privacy e retention | intenzionalmente minima | mantenere il minimo necessario; se arrivano documenti/Alloggiati servono finalità, retention, cancellazione, access log e ruoli granulari | P0 |
| Accessibilità e mobile | parziale | niente overflow, focus/keyboard, tap target, primo comando entro viewport, uso in movimento e su rete instabile | P0 |
| Coerenza prodotto | fragile | nomenclatura, CTA, stati, layout e livello di dettaglio coerenti tra Dashboard, Ricettività, Workspace, Planning, Report e Cassa | P0 |

## Cosa insegnano i competitor

Questi sono pattern dichiarati da fonti ufficiali; non sono assunzioni di copertura reale da contratto.

- [Zucchetti Suite 5](https://www.zucchetti.com/en/cms/ENG/industries/hospitality/hotellerie/property-management-system/suite-5/software-pms-functionalities.html) mette in primo piano DayByDay con in-house, arrivi, partenze e comandi rapidi, oltre a dashboard di controllo, revenue e multi-property. La lezione è una superficie comune front office–direzione–reparti, non dashboard isolate.
- [Mews Essentials](https://help.mews.com/s/article/Understanding-the-Essentials-pricing-plan?language=en_US) raggruppa nella proposta base PMS, booking engine, guest portal, rate management, housekeeping, connectivity, reporting, kiosk e allotment. Il mercato si aspetta un percorso ospite completo già dal piano d’ingresso.
- [Cloudbeds API](https://developers.cloudbeds.com/page/home) espone come oggetti integrabili ospiti, prenotazioni, check-in/out, housekeeping, room access, POS, accounting, insight e distribuzione. Per competere serve una superficie API/versionata, non solo route HTML interne.
- [RoomRaccoon](https://roomraccoon.com/solutions/hotel-management-software/) unisce prenotazioni, rate, pagamenti, check-in/out, housekeeping, invoice/reporting, gruppi, allotment, upsell e ID scanner; la documentazione cita inoltre [dynamic pricing](https://contact.roomraccoon.com/en/support/solutions/articles/150000190574-dynamic-pricing-faqs) e gestione di payment links/refund/VCC.
- [SiteMinder Channel Manager](https://www.siteminder.com/channel-manager/) vende distribuzione real-time, regole di yield/stop-sell e centinaia di canali con connessioni PMS/RMS. Un campo `canale=OTA` non equivale a distribuzione.
- [Mews/Cloudbeds housekeeping](https://help.mews.com/s/article/space-status-report) e [Cloudbeds room conditions](https://myfrontdesk.cloudbeds.com/hc/en-us/articles/216540808-Housekeeping-room-conditions) mostrano la necessità di distinguere pulizia, ispezione, blocco manutenzione e vendibilità commerciale. In particolare “dirty” non deve significare automaticamente “non vendibile”.

## Specificità italiane non rinviabili

- [Alloggiati Web](https://alloggiatiweb.poliziadistato.it/PortaleAlloggiati/) richiede la comunicazione delle generalità entro 24 ore dall’arrivo, o all’arrivo per soggiorni inferiori a 24 ore; la ricevuta va conservata secondo le istruzioni del portale.
- [Garante Privacy](https://www.garanteprivacy.it/home/docweb/-/docweb-display/docweb/10244195) indica che copie/immagini dei documenti non vanno conservate oltre il tempo strettamente necessario alla trasmissione; la retention deve essere progettata per finalità, non per comodità tecnica.
- [Istat — Movimento clienti](https://indata.istat.it/mtur/) richiede dati mensili su arrivi/presenze per territorio, categoria/tipologia e provenienza, con procedure di invio e indicatori di capacità.
- [Chekin API](https://docs.chekin.com/) è un benchmark concreto per flusso dati, ricevute, webhook e invio alle autorità: eventuali integrazioni locali devono avere esito, retry, audit e riconciliazione espliciti.

## Limiti tecnici da risolvere

### Architettura

Il prodotto usa WSGI Python standard library e SQLite, con WAL, `BEGIN IMMEDIATE`, `synchronous=FULL`, timeout busy di 5 secondi e un server configurato a 32 worker: è una scelta semplice e adatta a installazioni locali, ma crea un ceiling su concorrenza, integrazioni e operazioni distribuite. Il codice Hospitality principale è concentrato in un modulo di circa 6.500 righe; aggiungere rate, folio, PSP, connettori e adempimenti nello stesso punto aumenterebbe il rischio di regressioni.

Non risultano una superficie `/api` Hospitality, OpenAPI o webhook runtime nella codebase cercata. Per il prossimo salto servono almeno:

- API versionata per guest, inventory, reservations, stays, folio e housekeeping;
- provider contract per Alloggiati, Istat, PSP, channel manager e booking engine;
- outbox/inbox idempotente, retry con backoff, dead-letter e riconciliazione;
- source-of-truth esplicito per disponibilità, denaro, identità e adempimenti.

Il thread scheduler locale esegue in sequenza purge, backup, restore drill, reminder, outbox e comunicazioni. Può bastare per un’installazione piccola, ma non è sufficiente da solo per callback esterni, retry, job lunghi e garanzie di consegna: un backup lento può ritardare un messaggio ospite. Inoltre l’executor accetta richieste senza un limite applicativo esplicito di coda, quindi sotto overload servono back-pressure, timeout e fail-fast. Nessuna chiamata esterna deve tenere un lock SQLite aperto.

### Sicurezza, privacy e deploy

La CSP corrente mantiene `style-src 'unsafe-inline'`; nella superficie Hospitality sono presenti 19 attributi `style=` e 6 handler inline (`onclick`, `onchange`, `onsubmit`). Prima di introdurre guest PII, documenti o pagamenti occorre spostare comportamenti e stili in asset versionati, definire audit log per accesso/modifica/esportazione e implementare retention per finalità.

Backup, restore, RPO/RTO, rete assente e procedura di recovery devono essere provati su un’installazione reale. Un export CSV non è un piano di continuità.

La retention del pre-check-in è dichiarata nel modello (`retention_until`) e possiede un dry-run, ma l’audit non ha trovato un purge Hospitality applicativo che dimostri la cancellazione effettiva. Prima di raccogliere più PII servono apply-mode idempotente, audit della cancellazione e coerenza con backup/export. L’osservabilità è utile ma locale e bounded: campiona request/job in SQLite, senza una prova di monitoraggio fleet-wide o tracing distribuito.

### UI e performance percepita

La cattura mostra:

- Dashboard iniziale ancora HSE/HR-first: per un receptionist il primo task non è visibile;
- Oggi desktop con molto spazio vuoto e carte operative concentrate in una colonna stretta;
- Oggi mobile con nome/metadati che si spezzano in colonne troppo strette;
- Workspace mobile con azioni “Assegna” che escono dal viewport;
- Report mobile lunghissimo e con tabelle metriche che mantengono una forma desktop invece di diventare cards o viste progressive;
- checkout leggibile e guidato, ma molto lungo e ancora esplicitamente manuale, senza PSP o documento fiscale.

La regola di qualità dovrebbe essere: ogni route operativa ha un solo “prossimo comando”, visibile senza scroll iniziale su 390px, e non contiene dati che l’operatore non può usare in quel momento.

## Stato della base BI

Il catalogo è abbastanza ampio per guidare le decisioni, ma non ancora abbastanza rigoroso per automatizzare claim normativi o finanziari:

- 36 bundle Hospitality, 155 source entry, 141 URL uniche;
- 240 claim, 422 fact, 642 feature e 285 record tecnici;
- 234 candidate nel registry: 26 `new`, 24 `researching`, 158 `qualified`;
- 731 cache row: 684 ready, 30 failed, 12 blocked; 246 ready sono oltre la data di refresh;
- 74 cache entry Hospitality, ma solo 43 con content hash e nessuna collegata a `source_id` del catalogo;
- le fonti regolatorie primarie per Alloggiati, Istat, Garante, Agenzia delle Entrate e tassa comunale sono ancora da impacchettare.

Quindi la prossima ricerca deve privilegiare autorità normativa, profondità tecnica degli API, deduplica e refresh; non altra discovery indiscriminata. Le fonti vendor vanno conservate come claim dichiarati, separati da “osservato”, “non osservato” e “non supportato”.

## Piano di miglioramento ordinato

### Wave P0 — rendere il prodotto coerente e pilotabile

1. Profilo Hospitality e home “Oggi” con contesto struttura persistente.
2. Fix visuali: layout delle stay cards, workspace 390px, report responsive, density desktop, azioni primarie.
3. Correggere il contratto unità eliminata/soggiorno e riportare la suite completa a verde.
4. Separare categoria vendibile, unità fisica e prenotazione non assegnata.
5. Modellare ospiti per persona e ruoli booker/ospite/pagante; mantenere il minimo PII.
6. Chiudere il ciclo pulizia–ispezione–manutenzione–vendibilità.

### Wave P1 — completare il turno economico e regolatorio

1. Rate plan e condizioni di cancellazione/no-show/caparra.
2. Folio completo, split, extra, storni/rimborsi, sessione cassa e night audit.
3. Adapter Alloggiati, Istat e tassa di soggiorno, con ricevute/errori/retry.
4. PSP/fiscalità solo dopo aver scelto provider, responsabilità e source-of-truth.
5. Inbox e messaggistica eventi con consenso e delivery status.
6. Reporting ADR/RevPAR/pickup/channel netto e carico housekeeping.

### Wave P2 — aumentare il mercato servibile

1. API e connettori channel manager/booking engine.
2. Gruppi con rooming list/allotment, corporate/agencies e multi-property.
3. F&B/POS/food cost, spa/activities e camping/access control solo con clienti pilota che lo richiedano.
4. Offline/degraded mode, osservabilità, import/migrazione e strumenti di adozione.

## Fleet e lock operativi

Le sei fleet Luna sono state avviate in sola lettura. Ogni fleet ha un lock logico, un perimetro non sovrapposto e un output integrabile; nessuna deve modificare la codebase durante la fase di diagnosi.

| Fleet | Lock | Output |
|---|---|---|
| UX/competition | `UX-COMP-01` | delta osservabili su IA, workflow, competitor e front desk |
| PMS domain | `DOMAIN-PMS-01` | matrice implemented/partial/absent per modello e verticali |
| Technical limits | `TECH-LIMITS-01` | rischi architetturali, sicurezza, API, performance e acceptance test |
| Visual QA | `VISUAL-QA-01` | audit screenshot 390/1440 con route, selector e ordine fix |
| QA/pilot | `QA-PILOT-01` | scenari, dati fixture, release gate e metriche di campo |
| BI/source quality | `BI-SOURCES-01` | fonti mancanti, freshness, deduplica e backlog di ricerca |

Per la fase di implementazione, i lock di scrittura devono essere disgiunti:

- `WRITE-UI`: templates, componenti e CSS Hospitality;
- `WRITE-DOMAIN`: nuovi modelli/migrazioni/domain services;
- `WRITE-INTEGRATIONS`: provider, outbox, webhook e adapter;
- `WRITE-QA`: test, fixture, report e gate.

La registrazione delle URL e delle candidate research va fatta con [`scripts/research_registry.py`](../../scripts/research_registry.py): una URL riservata una sola volta, cache locale riusabile, claim con fonte e data di recupero. La codebase del prodotto resta congelata per la diagnosi; dopo il triage ogni agent riceve file ownership esplicita.

## Definition of done

Prima di dichiarare il verticale competitivo:

- 390px e 1440px senza overflow sui flussi core e con primo comando visibile;
- Dashboard, Oggi, Workspace, Planning, Pulizie, Soggiorno, Checkout e Report usano la stessa grammatica di stati e CTA;
- categoria/unità, ospite/persona, booker/pagante, rate/folio e housekeeping hanno invarianti testate;
- due operatori concorrenti non possono vendere l’ultima unità o duplicare un incasso;
- Alloggiati/Istat/tassa hanno esito, retry, ricevuta, retention e audit;
- ogni integrazione ha source-of-truth, mapping, idempotenza e procedura di riconciliazione;
- suite completa e gate Hospitality verdi, più pilot reale con i 17 scenari Q01–Q17 del dossier QA.

La copertura browser attuale non prova ancora: creazione prenotazione end-to-end, ciclo camera sporca → QC → arrivo, richiesta ospite → assegnazione → chiusura, apertura/conteggio/chiusura cassa, restore, ruoli reception/piani/admin, due browser concorrenti, JavaScript disabilitato, keyboard/focus, 320px, zoom 200% e accessibilità automatizzata. Le soglie di pilot da usare come gate sono: almeno 90% dei task essenziali completati senza aiuto, zero duplicazioni di denaro/inventario, zero scope leak, Oggi/planning p95 ≤500ms sul fixture M e RPO/RTO misurati su dati reali.

## Dossier correlati

- [Gap G01–G60](../../../../gestionale-anagrafica/docs/roadmap/hospitality/revisione-prodotto-2026-09/completamento/01-gap-prioritari.md)
- [Piano eseguibile RX-026..041](../../../../gestionale-anagrafica/docs/roadmap/hospitality/revisione-prodotto-2026-09/completamento/04-piano-eseguibile.md)
- [QA e pilot](../../../../gestionale-anagrafica/docs/roadmap/hospitality/revisione-prodotto-2026-09/completamento/05-qa-e-pilota.md)
- [Modello dati del catalogo](../../docs/data-model.md)
