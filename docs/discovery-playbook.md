# Discovery di gestionali italiani

L'obiettivo iniziale è massimizzare il richiamo (trovare candidati), poi validare e arricchire
solo quelli che sono effettivamente prodotti software gestionali italiani o venduti in Italia.

## Funnel a tre passaggi

```text
fonti ad alto richiamo → candidati deduplicati → schede verificate e arricchite
```

1. **Discovery**: raccogliere nome prodotto, azienda, dominio e URL della pagina di evidenza.
   Non cercare di compilare tutte le feature in questa fase.
2. **Qualificazione**: verificare che esista un prodotto gestionale identificabile e associare,
   quando possibile, P.IVA, ragione sociale e codice ATECO con versione/fonte.
3. **Enrichment**: acquisire fonti ufficiali, feature, caratteristiche tecniche, pricing e
   metriche finanziarie, sempre con claim ed evidenza.

## Fonti e query ad alto richiamo

- Directory e marketplace software italiani, associazioni di categoria e partner ERP/CRM/POS.
- Pagine ufficiali con formule come `software gestionale`, `ERP`, `gestionale cloud`,
  `fatturazione elettronica`, `software per [verticale]`.
- Verticali: retail/POS, hospitality, ristorazione, studi professionali, edilizia, produzione,
  logistica, sanità, autosaloni, agricoltura, e-commerce, HR e paghe.
- Sitemap e sezioni `/prodotti`, `/soluzioni`, `/funzionalita`, `/prezzi`, `/integrazioni`,
  `/api`, `/documentazione` dei domini già qualificati.
- Footer legali, privacy policy, contatti e condizioni: spesso forniscono ragione sociale e
  P.IVA. I registri e i bilanci sono fonti preferibili per ATECO e metriche societarie.

## Trucchi di deduplicazione e priorità

- Chiave forte dell'azienda: P.IVA; chiave forte del prodotto: azienda canonica + slug prodotto.
- Chiavi di appoggio: dominio registrabile, ragione sociale normalizzata, nomi/brand alternativi.
- Prima di aprire un URL, usare il registro: lo stesso contenuto con parametri `utm` diversi
  risolve alla stessa URL canonica.
- Dividere i lavori per verticale o fonte, mai semplicemente per query; usare lease brevi sugli
  URL per le eccezioni inevitabili.
- Tenere candidati separati da record verificati: una directory può generare falsi positivi.
- Assegnare priorità maggiore a candidati con dominio proprio, prodotto nominato, P.IVA o pagina
  ufficiale; minore a rivenditori, servizi di consulenza e risultati non verificabili.

Il registro ha anche una coda di candidati, separata dagli URL:

```bash
python3 scripts/research_registry.py candidate-add --name 'Nome prodotto' \
  --company 'Azienda S.r.l.' --vat-id 01234567890 --website 'https://azienda.example' \
  --method 'directory-erp' --priority 80
python3 scripts/research_registry.py candidate-claim-next \
  --agent research-erp-02 --purpose qualification
```

La P.IVA deduplica l'azienda; in sua assenza la chiave è deterministica da prodotto, azienda e
dominio. Dopo la verifica il ricercatore chiude il lease con `candidate-complete`, scegliendo
`qualified`, `rejected` o `duplicate`.

## Indicazioni tecniche da cercare

Non inferire lo stack da supposizioni. Cercare dichiarazioni su deployment/cloud/on-premise,
browser o app mobile, API e protocolli, integrazioni, SSO/autenticazione, sicurezza/certificazioni,
residenza dati, database e SDK. Se un dettaglio è ricavato da HTML, documentazione API o un PDF,
registrarlo come osservazione con URL ed estratto; se è un'ipotesi, salvarlo come `claim` inferito.
