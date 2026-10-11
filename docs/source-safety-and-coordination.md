# Sicurezza delle fonti e coordinamento degli agenti

## Principio operativo

Prima di visitare una pagina, ogni agente deve riservare l'URL nel registro locale:

```bash
python3 scripts/research_registry.py reserve \
  --url 'https://vendor.example/funzionalita?utm_source=...' \
  --agent research-retail-03 --purpose 'feature inventory'
```

Il risultato è JSON:

- `leased`: l'agente può lavorare sulla fonte e deve completare/rilasciare il lease;
- `cached`: esiste già una copia/estrazione fresca, da riusare senza nuova visita;
- `busy`: un altro agente sta lavorando sulla stessa URL; passare a un altro target.

Tracking parameters e frammenti vengono rimossi nella canonicalizzazione. Il lease scade per
evitare blocchi permanenti. La cache è separata dal catalogo e supporta molte letture: le sue
scritture sono transazioni SQLite brevissime in WAL.

Per fonti già esaminate senza un nuovo fetch:

```bash
python3 scripts/research_registry.py complete \
  --url 'https://vendor.example/funzionalita' --agent research-retail-03 --status ready \
  --metadata-json '{"source_id": 42, "refresh_after": "2026-08-30T00:00:00+00:00"}'
```

## Acquisizione prudente

`safe_fetch.py` è opzionale e acquisisce una sola fonte dopo averne ottenuto il lease.

```bash
# Predefinito: conserva solo metadati, hash e dati HTTP; non salva il corpo.
python3 scripts/safe_fetch.py --url 'https://vendor.example/listino.pdf' \
  --agent research-erp-01 --purpose pricing

# Conserva solo testo estratto da HTML/testo, mai un PDF; richiede una base di conservazione.
python3 scripts/safe_fetch.py --url 'https://vendor.example/funzionalita' \
  --agent research-erp-01 --purpose features \
  --retention excerpt --rights-basis publicly_available

# Salva l'artefatto grezzo soltanto dopo aver valutato autorizzazione/diritti.
python3 scripts/safe_fetch.py --url 'https://vendor.example/brochure.pdf' \
  --agent research-erp-01 --purpose brochure \
  --retention artifact --rights-basis permission
```

Il tool rifiuta host locali/privati, URL con credenziali, eseguibili e archivi, impone timeout e
limiti dimensionali, segue solo redirect verso host pubblici, non usa cookie e non renderizza né
esegue HTML/PDF/JavaScript. Un PDF viene archiviato come blob opaco: non viene aperto né parsato
automaticamente. Nessuna di queste misure sostituisce un antivirus; prima di aprire un artefatto
fuori dall'ambiente isolato va effettuata una scansione con il software di sicurezza disponibile.

Non assumere che “pubblicamente accessibile” significhi automaticamente riutilizzabile. Per ogni
artefatto conservato registrare la base scelta (`publicly_available`, `permission`, `public_domain`
o `internal`) e rispettare termini del sito, copyright, privacy, robots.txt e limiti contrattuali.

## Riuso nel catalogo

Il bundle JSON continua a essere il solo input del catalogo. Inserire nello `source` del bundle
l'URL canonico, hash, data di recupero e gli estratti impiegati. Se la fonte è già presente,
riusare `source_id`, documento e chunk esistenti anziché ripetere la navigazione.
