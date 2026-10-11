# Modello dati

Il database usa un modello ibrido: normalizza ciò che serve per confronti e visualizzazioni,
ma conserva dati testuali e dettagli atipici senza cambiare schema.

## Livelli dell'informazione

```text
bundle JSON immutabile → importatore → SQLite / FTS5 → query e visualizzazioni
                                  ├─ entità e relazioni normalizzate
                                  ├─ documenti e passaggi testuali ricercabili
                                  └─ facts, claims e metadata JSON per l'eterogeneità
```

Le tabelle principali sono:

| Gruppo | Tabelle | Uso |
| --- | --- | --- |
| Anagrafica | `company_groups`, `companies`, `industry_codes`, `company_industry_codes`, `products` | Gruppi, produttori, classificazioni ATECO e prodotti. |
| Tassonomia | `taxonomy_terms`, `product_terms`, `features`, `product_features` | Categorie, verticali, segmenti e funzionalità business. |
| Tecnologia | `technical_terms`, `product_technical_terms` | Caratteristiche tecniche confrontabili, con evidenza. |
| Evidenze | `sources`, `documents`, `document_chunks`, `claims` | URL, testo estratto ed estratti citabili. |
| Analisi | `financial_metrics`, `facts`, `notes` | Numeri comparabili, dati rari e valutazioni esplicite. |
| Audit | `imports` | Idempotenza e provenienza del bundle importato. |

## Regole di modellazione

- Una colonna o relazione dedicata va aggiunta quando il dato è ricorrente e servirà a filtri,
  grafici o mappe.
- `metadata_json` è per dettagli non ricorrenti associati a un'entità o a una fonte.
- `facts` contiene osservazioni strutturate ma non ancora promosse a modello dedicato.
- Le caratteristiche tecniche ricorrenti sono termini normalizzati: modello di deployment,
  API/protocolli, piattaforme client e mobile, database, stack dichiarato, cloud/hosting,
  autenticazione, sicurezza, localizzazione dei dati, integrazione hardware, auditabilità ed estensibilità. Versioni, limiti e
  dettagli rari restano in `facts` con predicati `technical.*` o in `metadata_json`.
- `documents` conserva il testo estratto; `document_chunks` lo spezza per la ricerca FTS5.
- Ogni classificazione, feature, metrica finanziaria, fact e claim deve avere una fonte e,
  quando disponibile, un breve `evidence_excerpt`.
- Una nota è sempre un'analisi dell'agente; non sostituisce un dato osservato.
- Le note possono anche documentare la qualità della fonte o la motivazione di una
  classificazione; restano separate dai claim osservati.
- Il codice ATECO è una classificazione dell'azienda, non del singolo prodotto. Si memorizzano
  codice, versione della classificazione, ruolo primario/secondario, validità e fonte; la
  P.IVA resta l'identificatore più affidabile per associare il codice alla società.

## Fatturato e altre metriche

Il fatturato deve sempre specificare il soggetto (`company`, `product` o `group`), l'anno,
la valuta e il tipo di valore:

- `reported`: valore dichiarato o proveniente da un bilancio;
- `estimated`: stima esplicita, con metodologia;
- `derived`: calcolo derivato da altri valori.

Il valore può essere esatto o un intervallo. Il fatturato dell'azienda non deve essere
presentato come fatturato del prodotto senza un passaggio metodologico esplicito.

## Visualizzazioni già supportate

- Matrice prodotto × feature e heatmap di copertura funzionale.
- Matrice prodotto × caratteristica tecnica, ad esempio cloud/on-premise × API × sicurezza.
- Mappa categoria/verticale × segmento cliente, con bolla basata sull'ultimo fatturato noto.
- Grafo azienda → prodotto → categoria/feature.
- Ricerca locale nel testo di fonti e note, con ritorno del passaggio pertinente.
- Ranking per numero di feature, copertura di segmenti e confidenza delle evidenze.
