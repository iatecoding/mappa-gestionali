# Workflow di ricerca

## Ruoli

- **Research**: individua fonti e deposita un bundle JSON in `data/inbox/`.
- **Curation**: corregge tassonomia, duplicati e confidenza con un nuovo bundle.
- **Import/QA**: valida e importa in SQLite.

## Regole per le fonti

- Conservare sempre URL canonico e data di recupero.
- Inserire un estratto breve che sostenga il claim; il testo intero estratto è opzionale ma
  molto utile per ricerca e revisione.
- Distinguere fonti ufficiali, registri/bilanci, stampa, directory e inferenze.
- Non salvare una pagina intera o un PDF quando non necessario o non consentito: URL, hash e
  passaggi rilevanti sono normalmente sufficienti.

## Tassonomia iniziale

Usare identificatori in inglese, stabili e `snake_case`; l'etichetta può restare in italiano.

| Tipo | Esempi iniziali |
| --- | --- |
| `category` | `erp`, `accounting`, `crm`, `hr`, `pos`, `industry_4_0` |
| `vertical` | `retail`, `hospitality`, `manufacturing`, `construction`, `healthcare` |
| `segment` | `micro_business`, `sme`, `mid_market`, `enterprise`, `accounting_firms` |
| Feature | `e_invoicing`, `general_ledger`, `inventory_management`, `crm`, `api`, `ai_assistance` |

Per le caratteristiche tecniche, usare `technical_characteristics` nel bundle solo quando una
fonte lo dichiara esplicitamente. Esempi di `kind`: `deployment_model`, `api_protocol`,
`authentication`, `security_standard`, `database`, `cloud_provider`. Per dettagli come
versioni minime, limiti API o configurazioni, usare invece un `fact` con un predicato
`technical.*` e un valore JSON.

Per ATECO, usare `industry_classifications` con `company_ref`, `classification_system`,
`classification_version`, `code`, `role` e `source_ref`. Non omettere la versione: le
classificazioni cambiano nel tempo e un codice privo di versione può essere ambiguo.

Una tassonomia può crescere con nuovi termini, ma non si rinomina uno slug già pubblicato:
si aggiunge un alias o un termine nuovo.

## Comandi

```bash
python3 scripts/init_db.py
python3 scripts/validate_inbox.py data/inbox/2026-07
python3 scripts/import_inbox.py data/inbox/2026-07
python3 scripts/query_examples.py
python3 scripts/completeness_report.py
```

L'importazione è seriale per scelta: SQLite gestisce moltissime letture in parallelo, ma un
solo importatore evita conflitti di scrittura. L'inbox è quindi il confine sicuro tra agenti.

`completeness_report.py` produce un controllo riproducibile delle coperture minime (feature,
dettagli tecnici, segnali commerciali, dati finanziari e P.IVA) e mostra i primi soggetti da
assegnare al ciclo di ricerca successivo. Un'assenza non viene interpretata come una
caratteristica negativa: indica solo che manca ancora un'evidenza salvata.

Se un import crea un doppione già dimostrato da identità e URL coincidenti, la riconciliazione
non è automatica: si verifica prima il piano e poi lo si applica in un'unica transazione.

```bash
python3 scripts/merge_catalog_duplicates.py --product DUPLICATO:CANONICO --company DUPLICATA:CANONICA
python3 scripts/merge_catalog_duplicates.py --apply --product DUPLICATO:CANONICO --company DUPLICATA:CANONICA
```

Lo script trasferisce tutte le evidenze al record canonico e richiede esplicitamente gli ID:
non usa corrispondenze fuzzy e non va eseguito per mere somiglianze di nome.
