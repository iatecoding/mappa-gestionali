# Intelligence per moduli HR e HSE

Questo progetto confronta ciò che i prodotti dichiarano di supportare; non deduce che una
funzione assente dal catalogo sia assente dal prodotto. Lo scopo è individuare moduli da
integrare o da differenziare in un nuovo applicativo.

## Quattro livelli da non confondere

| Livello | Dove si salva | Esempio |
| --- | --- | --- |
| Capacità prodotto osservata | `features` | gestione ferie, DVR, corsi, recruiting |
| Meccanismo tecnico osservato | `technical_characteristics` o `facts` | API REST, SSO, app mobile, terminale badge |
| Integrazione o vincolo osservato | `facts` | connettore payroll, supporto offline, dispositivo compatibile |
| Lettura competitiva | `claims` | modulo consigliato, complessità, mercato e moat hardware |

Le prime tre righe richiedono una fonte ufficiale. La quarta è sempre una valutazione
esplicitamente `inferred`, con metodologia e confidenza: non va presentata come affermazione del
fornitore.

## Vocabolario dei moduli

Usare feature piccole e combinabili. Dove necessario si aggiunge una classificazione `segment`
o `vertical` per il mercato interessato.

| Dominio | Moduli da osservare | Mercato / acquirente tipico |
| --- | --- | --- |
| HR core | anagrafica dipendente, workflow, documentale, firma, self-service | PMI e mid-market |
| Tempo e workforce | presenze, turni, assenze, pianificazione, timesheet, trasferta | aziende con personale operativo, retail, servizi |
| Talent | recruiting, ATS, onboarding, performance, formazione, skill matrix | HR strutturato e aziende in crescita |
| Payroll | paghe, CU, adempimenti, simulazioni, integrazione studio | consulenti del lavoro e PMI italiane |
| HSE core | DVR, valutazione rischi, scadenziario, sorveglianza sanitaria, DPI | PMI, industria, cantieri |
| HSE operativo | audit, incidenti, non conformità, azioni correttive, permessi | industria regolata e gruppi multi-sito |
| Formazione obbligatoria | catalogo corsi, attestati, scadenze, e-learning, aula | HSE, edilizia, provider formazione |
| Field / cantiere | verbali, sopralluoghi, checklist, offline, geolocalizzazione | edilizia, facility e manutenzione |

## Tecnologie e hardware da rilevare

Usare `technical_characteristics` per il meccanismo esplicitamente dichiarato e `facts` per
modello, limiti o nome del connettore.

- API, webhooks, import/export e protocolli; integrazioni con ERP, paghe e identity provider.
- SSO, MFA, ruoli, audit trail, firma elettronica e conservazione documentale.
- Web, app iOS/Android, offline e notifiche.
- Terminali presenze, badge RFID/NFC, controllo accessi, biometria solo se dichiarata,
  geolocalizzazione, sensori/IoT e DPI connessi.

L'hardware può aumentare il costo di sostituzione solo quando esistono evidenze di terminali,
installazione, connettori proprietari, dati storici o processi sul campo legati al prodotto.
Non basta la semplice compatibilità generica per dichiarare un moat.

## Valutazione dell'implementazione

Salvare la valutazione come claim `inferred` con predicato
`module.implementation_complexity` e assessment `low`, `medium`, `high` oppure `very_high`.
La metodologia deve citare i driver osservati.

| Livello | Driver tipici |
| --- | --- |
| `low` | CRUD, workflow semplice, notifiche, export standard, nessun dato regolato |
| `medium` | ruoli, approvazioni configurabili, mobile, import, integrazione API singola |
| `high` | paghe/adempimenti, SSO enterprise, audit immutabile, offline, connettori multipli |
| `very_high` | hardware/biometria, calcolo normativo, multi-tenant enterprise, IoT sul campo, firma/conservazione regolata |

La complessità è riferita a un'applicazione nuova e non al prezzo o alla qualità del concorrente.
Per ogni claim di complessità aggiungere, quando utile, `module.market_fit` e
`module.hardware_moat` come ulteriori claim inferiti.

## Priorità di ricerca

1. Verificare prima le interfacce e i confini: API, SSO, import/export, mobile/offline,
   terminali e dispositivi.
2. Raccogliere poi le feature business atomiche, senza comprimere più moduli in una feature vaga.
3. Tracciare gli elementi regolati e gli effetti di rete/dati storici come driver competitivi.
4. Solo alla fine stimare complessità e mercato, mantenendo la relativa inferenza separata.
