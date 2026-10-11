#!/usr/bin/env python3
"""Export an enriched, structured Business Intelligence payload for the web hub."""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# Macro-sector definitions (clean typography, no emojis)
MACRO_SECTOR_SPECS = [
    {
        "id": "erp_finance",
        "name": "ERP, Finanza & Controllo",
        "slug": "erp_finance",
        "description": "Sistemi ERP completi, contabilità generale e analitica, fatturazione elettronica SDI e bilancio.",
    },
    {
        "id": "hr_workforce",
        "name": "HR, Paghe & Gestione Personale",
        "slug": "hr_workforce",
        "description": "Elaborazione buste paga, rilevazione presenze, timbrature, turni, talent management e welfare aziendale.",
    },
    {
        "id": "public_utilities",
        "name": "Pubblica Amministrazione & Utility",
        "slug": "public_utilities",
        "description": "Sistemi per enti locali, gestione tributi, fatturazione rifiuti (TARI), idrico, gas e servizi pubblici.",
    },
    {
        "id": "services_health_sports",
        "name": "Professioni, Salute, Sport & No-Profit",
        "slug": "services_health_sports",
        "description": "Gestionali verticali per studi legali, medici, palestre con tornelli, ASD/SSD, scuole e terzo settore.",
    },
    {
        "id": "logistics_transport",
        "name": "Logistica, Magazzino & Flotte",
        "slug": "logistics_transport",
        "description": "WMS per magazzini intensivi, TMS per trasporti e spedizioni, gestione flotte e telemetria veicoli.",
    },
    {
        "id": "retail_commerce",
        "name": "Retail, Cassa & E-commerce",
        "slug": "retail_commerce",
        "description": "Soluzioni per negozi fisici, registratori telematici RT, omnichannel retail e commercio elettronico.",
    },
    {
        "id": "field_construction",
        "name": "Field Service, Cantieri & Manutenzione",
        "slug": "field_construction",
        "description": "Gestione commesse edili, computi metrici, manutenzione impianti (CMMS) e tecnici sul campo.",
    },
    {
        "id": "industry_manufacturing",
        "name": "Manifattura & Industria 4.0",
        "slug": "industry_manufacturing",
        "description": "MES per avanzamento produzione, controllo qualità (QMS), LIMS, tracciabilità e Industrial IoT.",
    },
    {
        "id": "food_restaurant",
        "name": "Ristorazione & Food Service",
        "slug": "food_restaurant",
        "description": "Sistemi di cassa, presa comande, monitor cucina, delivery, HACCP e controllo scorte food & beverage.",
    },
    {
        "id": "hospitality",
        "name": "Hospitality & Strutture Ricettive",
        "slug": "hospitality",
        "description": "Software PMS per hotel, catene, residence, camping, B&B, channel manager e motori di prenotazione.",
    },
]

SPEC_BY_ID = {s["id"]: s for s in MACRO_SECTOR_SPECS}


def resolve_company_group(company_name: str, direct_group: str | None) -> str | None:
    """Determine group affiliation from explicit membership or corporate brand."""
    if direct_group:
        return direct_group
    name_lower = company_name.lower()
    if "zucchetti" in name_lower:
        return "Gruppo Zucchetti"
    if "teamsystem" in name_lower:
        return "Gruppo TeamSystem"
    if "wolters kluwer" in name_lower:
        return "Wolters Kluwer"
    if "deda" in name_lower or "dedalus" in name_lower:
        return "Deda Group / Dedalus"
    if "maggioli" in name_lower:
        return "Gruppo Maggioli"
    if "sistemi " in name_lower or name_lower == "sistemi s.p.a.":
        return "Sistemi S.p.A."
    if "var group" in name_lower or "sesa" in name_lower:
        return "Gruppo Sesa / Var Group"
    return None


def resolve_macro_sector(
    product_name: str,
    company_name: str,
    category_name: str,
    category_slug: str,
    terms: list[dict[str, object]],
    description: str | None,
) -> dict[str, str]:
    """Map a product to one of 10 coherent macro sectors based on taxonomy and semantic domain."""
    cat_text = f"{category_name} {category_slug}".lower()
    terms_text = " ".join(f"{t.get('name', '')} {t.get('slug', '')}" for t in terms).lower()
    p_text = product_name.lower()
    desc_text = (description or "").lower()

    # 1. Ristorazione / Food
    if any(k in cat_text or k in terms_text for k in [
        "ristoran", "ristoro", "pos per ristorazione", "restaurant", "food", "tavoli",
        "comande", "foodservice", "haccp", "tracciabilità alimentare"
    ]):
        spec = SPEC_BY_ID["food_restaurant"]
        return {"id": spec["id"], "name": spec["name"], "slug": spec["slug"], "description": spec["description"]}

    # 2. Hospitality / Hotel / Camping
    if any(k in cat_text or k in terms_text for k in [
        "hospitality_pms", "pms hospitality", "property management system", "property_management",
        "hotel", "camping", "campeggi", "channel manager", "booking engine", "hotel_distribution",
        "smart_access_hospitality", "guest_compliance", "affitti brevi", "bed and breakfast",
        "marina_management", "tour_activity"
    ]):
        spec = SPEC_BY_ID["hospitality"]
        return {"id": spec["id"], "name": spec["name"], "slug": spec["slug"], "description": spec["description"]}

    # 3. HR & Payroll
    if any(k in cat_text or k in terms_text for k in [
        "hr", "payroll", "paghe", "presenze", "timbratur", "personale", "recruiting",
        "welfare", "turni", "hcm", "hrms", "human_resource", "consulenti del lavoro", "labour_consultants", "time_attendance"
    ]):
        spec = SPEC_BY_ID["hr_workforce"]
        return {"id": spec["id"], "name": spec["name"], "slug": spec["slug"], "description": spec["description"]}

    # 4. Manifattura & MES
    if any(k in cat_text or k in terms_text for k in [
        "mes", "manufacturing", "manifattur", "produzione", "plm", "lims", "qualità", "quality", "industrial-iot", "digital twin"
    ]):
        spec = SPEC_BY_ID["industry_manufacturing"]
        return {"id": spec["id"], "name": spec["name"], "slug": spec["slug"], "description": spec["description"]}

    # 5. Logistica & WMS
    if any(k in cat_text or k in terms_text for k in [
        "wms", "magazzino", "logistica", "trasport", "spedizion", "tms", "flotte", "fleet", "shipping", "warehouse", "order-fulfillment"
    ]):
        spec = SPEC_BY_ID["logistics_transport"]
        return {"id": spec["id"], "name": spec["name"], "slug": spec["slug"], "description": spec["description"]}

    # 6. Field Service & Cantieri / Costruzioni / Manutenzione
    if any(k in cat_text or k in terms_text for k in [
        "cantiere", "cantieri", "costruzion", "construction", "edil", "computo", "cmms",
        "facility", "field service", "field_service", "manutenzion", "antincendio", "impianti"
    ]):
        spec = SPEC_BY_ID["field_construction"]
        return {"id": spec["id"], "name": spec["name"], "slug": spec["slug"], "description": spec["description"]}

    # 7. Retail & Cassa
    if any(k in cat_text or k in terms_text for k in [
        "retail", "punto cassa", "registratore", "e-commerce", "ecommerce", "dropshipping",
        "order management", "negozi", "shop", "farmaci", "beauty_salon", "dealer management", "dms"
    ]):
        spec = SPEC_BY_ID["retail_commerce"]
        return {"id": spec["id"], "name": spec["name"], "slug": spec["slug"], "description": spec["description"]}

    # 8. PA & Utility
    if any(k in cat_text or k in terms_text for k in [
        "pubblica amministrazione", "enti locali", "rifiuti", "utility", "telecom", "energia", "gas", "waste_management", "local_government"
    ]):
        spec = SPEC_BY_ID["public_utilities"]
        return {"id": spec["id"], "name": spec["name"], "slug": spec["slug"], "description": spec["description"]}

    # 9. Professioni, Salute, Sport & No-Profit
    if any(k in cat_text or k in terms_text for k in [
        "fitness", "palestr", "asd", "ssd", "sport", "legale", "avvocat", "studio legale",
        "medico", "clinica", "sanit", "associazion", "scuola", "scolastic", "lms", "formazione", "assicuraz", "condomin", "terzo settore"
    ]):
        spec = SPEC_BY_ID["services_health_sports"]
        return {"id": spec["id"], "name": spec["name"], "slug": spec["slug"], "description": spec["description"]}

    # 10. ERP & Finanza
    if any(k in cat_text or k in terms_text for k in [
        "erp", "contabilit", "accounting", "fiscal", "fattur", "fattura", "bilancio", "commercialist", "tributar", "aziendal", "pmi", "sme"
    ]):
        spec = SPEC_BY_ID["erp_finance"]
        return {"id": spec["id"], "name": spec["name"], "slug": spec["slug"], "description": spec["description"]}

    # Fallback using product name and description
    comb_desc = f"{p_text} {desc_text}"
    if any(k in comb_desc for k in ["hotel", "albergo", "campeggio", "residence", "b&b"]):
        spec = SPEC_BY_ID["hospitality"]
    elif any(k in comb_desc for k in ["ristorante", "pizzeria", "bar", "tavoli", "comande"]):
        spec = SPEC_BY_ID["food_restaurant"]
    elif any(k in comb_desc for k in ["cantiere", "edile", "costruzioni", "manutenzione"]):
        spec = SPEC_BY_ID["field_construction"]
    elif any(k in comb_desc for k in ["paghe", "cedolini", "presenze", "personale", "risorse umane"]):
        spec = SPEC_BY_ID["hr_workforce"]
    elif any(k in comb_desc for k in ["magazzino", "spedizioni", "logistica", "autotrasporti"]):
        spec = SPEC_BY_ID["logistics_transport"]
    elif any(k in comb_desc for k in ["fabbrica", "produzione", "mes", "industria"]):
        spec = SPEC_BY_ID["industry_manufacturing"]
    elif any(k in comb_desc for k in ["palestra", "fitness", "avvocato", "studio legale", "medico", "sanità"]):
        spec = SPEC_BY_ID["services_health_sports"]
    elif any(k in comb_desc for k in ["comune", "enti pubblici", "tributi", "rifiuti"]):
        spec = SPEC_BY_ID["public_utilities"]
    else:
        spec = SPEC_BY_ID["erp_finance"]

    return {"id": spec["id"], "name": spec["name"], "slug": spec["slug"], "description": spec["description"]}


def analyze_hardware(
    product_name: str,
    description: str | None,
    technical: list[dict[str, object]],
    terms: list[dict[str, object]],
    macro_id: str,
) -> dict[str, object]:
    """Classify hardware dependency and detect device classes."""
    tech_text = " ".join(str(t.get("name", "")) for t in technical).lower()
    terms_text = " ".join(str(t.get("name", "")) for t in terms).lower()
    desc_text = (description or "").lower()
    combined = f"{product_name.lower()} {desc_text} {terms_text} {tech_text}"

    devices: list[str] = []
    if any(k in tech_text or k in combined for k in ["pos", "rch", "custom", "cashmatic", "cassa", "stampante fiscale", "registratore telematico", "esc/pos"]):
        devices.append("Punto Cassa & Stampanti RT")
    if any(k in tech_text or k in combined for k in ["tornell", "varch", "controllo accessi", "barriere"]):
        devices.append("Tornelli & Varchi di Accesso")
    if any(k in tech_text or k in combined for k in ["timbratur", "timbratori", "badge", "marcatempo", "terminali presenze", "zbeacon", "iot reader", "nfc"]):
        devices.append("Terminali Timbratura & Badge")
    if any(k in tech_text or k in combined for k in ["smart lock", "serratur", "domotica", "keycard", "apriporta"]):
        devices.append("Smart Lock & Domotica")
    if any(k in tech_text or k in combined for k in ["barcode", "codici a barre", "rfid", "scanner", "palmare", "terminali portatili"]):
        devices.append("Scanner Barcode & Terminali Rugged")
    if any(k in tech_text or k in combined for k in ["gps", "geofence", "geolocalizzazione", "tachigrafo", "black box"]):
        devices.append("GPS & Telemetria Veicoli")
    if any(k in tech_text or k in combined for k in ["plc", "scada", "iot", "bilanc", "sensori", "bordo macchina"]):
        devices.append("IoT Industriale & PLC")

    has_explicit_hw = any(t.get("kind") == "hardware_integration" for t in technical)

    # Determine dependency level
    if len(devices) > 0 and (has_explicit_hw or any(d in devices for d in ["Punto Cassa & Stampanti RT", "Tornelli & Varchi di Accesso", "Terminali Timbratura & Badge", "IoT Industriale & PLC"])):
        level = "high"
        label = "Alta (hardware dedicato obbligatorio)"
        moat = "Forte barriera all'uscita (hardware dedicato e omologato installato sul campo)"
    elif len(devices) > 0:
        level = "medium"
        label = "Media (periferiche standard o sensori del telefono)"
        moat = "Integrazione di periferiche standard o sensori dello smartphone (costo di sostituzione moderato)"
    else:
        level = "none"
        label = "Bassa / Nulla (puro software in cloud)"
        moat = "Nessun vincolo fisico di installazione o hardware proprietario"

    return {
        "level": level,
        "label": label,
        "devices": devices,
        "moat": moat,
    }


def analyze_lock_in(
    company_name: str,
    group_name: str | None,
    product_name: str,
    description: str | None,
    technical: list[dict[str, object]],
    terms: list[dict[str, object]],
    hw_level: str,
) -> dict[str, object]:
    """Calculate vendor lock-in score and extract specific lock-in factors."""
    tech_text = " ".join(str(t.get("name", "")) for t in technical).lower()
    terms_text = " ".join(str(t.get("name", "")) for t in terms).lower()
    desc_text = (description or "").lower()
    combined = f"{product_name.lower()} {desc_text} {terms_text} {tech_text}"

    factors: list[str] = []
    is_conglomerate = bool(group_name)
    if is_conglomerate:
        factors.append(f"Suite integrata ({group_name}): lock-in da ecosistema multi-prodotto")

    has_normative = any(
        n in combined
        for n in ["sdi", "fatturapa", "fatturazione elettronica", "agenzia delle entrate", "uniemens", "f24", "alloggiati", "rentri", "pagopa", "inail"]
    )
    if has_normative:
        factors.append("Ancoraggio normativo / adempimenti fiscali italiani (SDI, F24, Paghe, RENTRI, Alloggiati)")

    has_api = any(
        t.get("kind") == "api_protocol"
        or "api" in str(t.get("name", "")).lower()
        or str(t.get("name", "")).lower() in ["ical", "stripe", "zapier", "rest"]
        for t in technical
    )
    if has_api:
        factors.append("API / Connettori standard documentati (fattore mitigatore di apertura)")
    else:
        factors.append("Nessuna API aperta documentata (chiusura flussi dati)")

    if hw_level == "high":
        factors.append("Costo di sostituzione hardware fisico installato (dispositivi in loco)")

    score = 2
    if is_conglomerate:
        score += 1
    if has_normative:
        score += 1
    if hw_level == "high":
        score += 1
    if has_api:
        score -= 1
    score = max(1, min(5, score))

    level = "high" if score >= 4 else ("medium" if score == 3 else "low")
    label = "Alto Lock-in" if level == "high" else ("Medio Lock-in" if level == "medium" else "Basso Lock-in (Aperto)")

    return {
        "level": level,
        "score": score,
        "label": label,
        "factors": factors,
    }


def analyze_pricing(pricing_items: list[dict[str, object]]) -> dict[str, object]:
    """Identify commercial transparency and pricing model."""
    has_numeric = False
    has_trial = False
    is_quote = False
    starting_price = None

    for item in pricing_items:
        pred = str(item.get("predicate", ""))
        val = item.get("value")
        if "trial" in pred or "demo" in pred:
            has_trial = True
        if isinstance(val, (int, float)) and val > 0:
            has_numeric = True
            if starting_price is None or val < starting_price:
                starting_price = val
        elif isinstance(val, dict):
            for k, v in val.items():
                if isinstance(v, (int, float)) and v > 0 and any(m in k for m in ["price", "exact", "eur", "amount", "fee", "cost"]):
                    has_numeric = True
                    if starting_price is None or v < starting_price:
                        starting_price = v
            if val.get("model") == "quote_based" or val.get("requires_contact") or val.get("numeric_price_public") is False:
                is_quote = True
            if val.get("trial"):
                has_trial = True

    if has_numeric:
        pricing_type = "public"
        pricing_label = "Prezzi pubblici verificati"
    elif has_trial:
        pricing_type = "trial"
        pricing_label = "Prova gratuita o demo in autonomia"
    elif is_quote:
        pricing_type = "quote"
        pricing_label = "Trattativa riservata / Preventivo"
    else:
        pricing_type = "undisclosed"
        pricing_label = "Non comunicato pubblicamente"

    return {
        "type": pricing_type,
        "label": pricing_label,
        "startingPrice": starting_price,
    }


def export_catalogue(database: Path, output: Path) -> int:
    """Write the comprehensive business intelligence payload and return product count."""
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row

    try:
        rows = connection.execute(
            """
            WITH primary_category AS (
                SELECT product_id, term_id
                FROM (
                    SELECT pt.product_id, pt.term_id,
                           row_number() OVER (PARTITION BY pt.product_id ORDER BY pt.rowid) AS rank
                    FROM product_terms pt
                    JOIN taxonomy_terms tt ON tt.id = pt.term_id
                    WHERE tt.kind = 'category'
                )
                WHERE rank = 1
            ),
            labour_consultants AS (
                SELECT DISTINCT pt.product_id
                FROM product_terms pt
                JOIN taxonomy_terms tt ON tt.id = pt.term_id
                WHERE tt.kind = 'segment' AND tt.slug = 'labour_consultants'
            ),
            latest_revenue AS (
                SELECT subject_id, period_year, value_exact, value_min, value_max, currency, value_kind
                FROM (
                    SELECT fm.*, row_number() OVER (
                        PARTITION BY fm.subject_id
                        ORDER BY fm.period_year DESC, fm.id DESC
                    ) AS rank
                    FROM financial_metrics fm
                    WHERE fm.subject_type = 'company' AND fm.metric = 'revenue'
                )
                WHERE rank = 1
            ),
            latest_employees AS (
                SELECT subject_id, period_year, value_exact
                FROM (
                    SELECT fm.*, row_number() OVER (
                        PARTITION BY fm.subject_id
                        ORDER BY fm.period_year DESC, fm.id DESC
                    ) AS rank
                    FROM financial_metrics fm
                    WHERE fm.subject_type = 'company' AND fm.metric = 'employees'
                )
                WHERE rank = 1
            ),
            latest_net_income AS (
                SELECT subject_id, period_year, value_exact
                FROM (
                    SELECT fm.*, row_number() OVER (
                        PARTITION BY fm.subject_id
                        ORDER BY fm.period_year DESC, fm.id DESC
                    ) AS rank
                    FROM financial_metrics fm
                    WHERE fm.subject_type = 'company' AND fm.metric = 'net_income'
                )
                WHERE rank = 1
            ),
            commercial_signal AS (
                SELECT subject_id, 1 AS present
                FROM facts
                WHERE subject_type = 'product'
                  AND (predicate LIKE 'pricing.%' OR predicate LIKE 'trial.%')
                GROUP BY subject_id
            )
            SELECT p.id, p.name AS product_name, p.website AS product_website, p.description,
                   c.id AS company_id, c.name AS company_name, c.website AS company_website,
                   CASE WHEN lc.product_id IS NOT NULL THEN 'Consulenti del lavoro'
                        ELSE coalesce(tc.name, 'Non classificato') END AS category_name,
                   CASE WHEN lc.product_id IS NOT NULL THEN 'labour-consultants'
                        ELSE coalesce(tc.slug, 'unclassified') END AS category_slug,
                   lr.period_year, lr.value_exact, lr.value_min, lr.value_max, lr.currency, lr.value_kind,
                   le.value_exact AS employees_count, le.period_year AS employees_year,
                   lni.value_exact AS net_income_value, lni.period_year AS net_income_year,
                   (SELECT count(*) FROM product_features pf WHERE pf.product_id = p.id) AS feature_count,
                   (SELECT count(*) FROM product_technical_terms ptt WHERE ptt.product_id = p.id) AS technical_count,
                   coalesce(cs.present, 0) AS commercial_signal
            FROM products p
            JOIN companies c ON c.id = p.company_id
            LEFT JOIN primary_category pc ON pc.product_id = p.id
            LEFT JOIN taxonomy_terms tc ON tc.id = pc.term_id
            LEFT JOIN labour_consultants lc ON lc.product_id = p.id
            LEFT JOIN latest_revenue lr ON lr.subject_id = c.id
            LEFT JOIN latest_employees le ON le.subject_id = c.id
            LEFT JOIN latest_net_income lni ON lni.subject_id = c.id
            LEFT JOIN commercial_signal cs ON cs.subject_id = p.id
            ORDER BY category_name COLLATE NOCASE, product_name COLLATE NOCASE
            """
        ).fetchall()

        # Company group memberships
        group_rows = connection.execute(
            """
            SELECT cgm.company_id, cg.name AS group_name
            FROM company_group_memberships cgm
            JOIN company_groups cg ON cg.id = cgm.group_id
            """
        ).fetchall()
        company_groups = {g["company_id"]: g["group_name"] for g in group_rows}

        # Features
        feature_rows = connection.execute(
            """
            SELECT pf.product_id, f.name, pf.support_level, pf.confidence
            FROM product_features pf
            JOIN features f ON f.id = pf.feature_id
            ORDER BY pf.product_id, f.name COLLATE NOCASE
            """
        ).fetchall()

        # Pricing
        pricing_rows = connection.execute(
            """
            SELECT subject_id AS product_id, predicate, value_text, value_number,
                   value_boolean, value_json, unit, confidence
            FROM facts
            WHERE subject_type = 'product'
              AND (predicate LIKE 'pricing.%' OR predicate LIKE 'trial.%')
            ORDER BY subject_id, predicate, id
            """
        ).fetchall()

        # Technical terms
        technical_rows = connection.execute(
            """
            SELECT ptt.product_id, tt.kind, tt.name, ptt.relationship_type, ptt.confidence
            FROM product_technical_terms ptt
            JOIN technical_terms tt ON tt.id = ptt.technical_term_id
            ORDER BY ptt.product_id, tt.kind, tt.name COLLATE NOCASE
            """
        ).fetchall()

        # Taxonomy terms
        term_rows = connection.execute(
            """
            SELECT pt.product_id, tt.kind, tt.slug, tt.name
            FROM product_terms pt
            JOIN taxonomy_terms tt ON tt.id = pt.term_id
            WHERE tt.kind IN ('category', 'vertical', 'segment')
            ORDER BY pt.product_id, tt.kind, tt.name COLLATE NOCASE
            """
        ).fetchall()

        # Claims
        claim_rows = connection.execute(
            """
            SELECT subject_id AS product_id, predicate, statement, claim_type, confidence
            FROM claims
            WHERE subject_type = 'product'
              AND predicate IN ('positioning', 'use_case')
            ORDER BY subject_id, id
            """
        ).fetchall()
    finally:
        connection.close()

    features_by_product: dict[int, list[dict[str, object]]] = {}
    for row in feature_rows:
        features_by_product.setdefault(row["product_id"], []).append(
            {"name": row["name"], "supportLevel": row["support_level"], "confidence": row["confidence"]}
        )

    pricing_by_product: dict[int, list[dict[str, object]]] = {}
    for row in pricing_rows:
        if row["value_json"] is not None:
            value: object = json.loads(row["value_json"])
        elif row["value_number"] is not None:
            value = row["value_number"]
        elif row["value_boolean"] is not None:
            value = bool(row["value_boolean"])
        else:
            value = row["value_text"]
        pricing_by_product.setdefault(row["product_id"], []).append(
            {"predicate": row["predicate"], "value": value, "unit": row["unit"], "confidence": row["confidence"]}
        )

    technical_by_product: dict[int, list[dict[str, object]]] = {}
    for row in technical_rows:
        technical_by_product.setdefault(row["product_id"], []).append(
            {"kind": row["kind"], "name": row["name"], "relationship": row["relationship_type"], "confidence": row["confidence"]}
        )

    terms_by_product: dict[int, list[dict[str, object]]] = {}
    for row in term_rows:
        terms_by_product.setdefault(row["product_id"], []).append(
            {"kind": row["kind"], "slug": row["slug"], "name": row["name"]}
        )

    claims_by_product: dict[int, list[dict[str, object]]] = {}
    for row in claim_rows:
        claims_by_product.setdefault(row["product_id"], []).append(
            {"predicate": row["predicate"], "statement": row["statement"], "claimType": row["claim_type"], "confidence": row["confidence"]}
        )

    all_products: list[dict[str, object]] = []
    company_dict: dict[int, dict[str, object]] = {}

    for row in rows:
        pid = row["id"]
        cid = row["company_id"]
        cname = row["company_name"]
        group_name = resolve_company_group(cname, company_groups.get(cid))
        p_tech = technical_by_product.get(pid, [])
        p_terms = terms_by_product.get(pid, [])
        p_pricing = pricing_by_product.get(pid, [])
        p_features = features_by_product.get(pid, [])
        p_claims = claims_by_product.get(pid, [])

        macro = resolve_macro_sector(
            product_name=row["product_name"],
            company_name=cname,
            category_name=row["category_name"],
            category_slug=row["category_slug"],
            terms=p_terms,
            description=row["description"],
        )

        hw_analysis = analyze_hardware(
            product_name=row["product_name"],
            description=row["description"],
            technical=p_tech,
            terms=p_terms,
            macro_id=macro["id"],
        )

        lock_analysis = analyze_lock_in(
            company_name=cname,
            group_name=group_name,
            product_name=row["product_name"],
            description=row["description"],
            technical=p_tech,
            terms=p_terms,
            hw_level=str(hw_analysis["level"]),
        )

        price_analysis = analyze_pricing(p_pricing)

        api_terms = [t["name"] for t in p_tech if t["kind"] == "api_protocol" or "api" in str(t["name"]).lower()]
        std_terms = [t["name"] for t in p_tech if t["kind"] == "integration_standard"]

        rev_val = row["value_exact"] or row["value_max"] or row["value_min"]

        if cid not in company_dict:
            company_dict[cid] = {
                "id": cid,
                "name": cname,
                "website": row["company_website"],
                "group": group_name,
                "revenue": rev_val,
                "revenueYear": row["period_year"],
                "revenueKind": row["value_kind"],
                "employees": row["employees_count"],
                "employeesYear": row["employees_year"],
                "netIncome": row["net_income_value"],
                "netIncomeYear": row["net_income_year"],
                "products": [],
            }
        company_dict[cid]["products"].append(row["product_name"])

        product_obj: dict[str, object] = {
            "id": pid,
            "name": row["product_name"],
            "website": row["product_website"],
            "company": cname,
            "companyId": cid,
            "companyGroup": group_name,
            "description": row["description"],
            "macroSector": macro["name"],
            "macroSectorId": macro["id"],
            "categoryName": row["category_name"],
            "categorySlug": row["category_slug"],
            "revenue": {
                "year": row["period_year"],
                "exact": row["value_exact"],
                "min": row["value_min"],
                "max": row["value_max"],
                "currency": row["currency"],
                "kind": row["value_kind"],
            }
            if row["period_year"] is not None
            else None,
            "employees": int(row["employees_count"]) if row["employees_count"] is not None else None,
            "netIncome": row["net_income_value"],
            "hardwareDependency": hw_analysis,
            "lockIn": lock_analysis,
            "pricingModel": price_analysis,
            "apiConnectivity": {
                "hasApi": bool(api_terms or std_terms),
                "protocols": api_terms,
                "standards": std_terms,
            },
            "featureCount": row["feature_count"],
            "technicalCount": row["technical_count"],
            "commercialSignal": bool(row["commercial_signal"]),
            "features": p_features,
            "pricing": p_pricing,
            "technical": p_tech,
            "terms": p_terms,
            "claims": p_claims,
        }
        all_products.append(product_obj)

    # Calculate Market Insights
    companies_list = list(company_dict.values())
    top_revenue_companies = sorted(
        [c for c in companies_list if c["revenue"] is not None and c["revenue"] > 0],
        key=lambda x: x["revenue"],
        reverse=True,
    )[:25]

    top_employee_companies = sorted(
        [c for c in companies_list if c["employees"] is not None and c["employees"] > 0],
        key=lambda x: x["employees"],
        reverse=True,
    )[:20]

    total_revenue_observed = sum(c["revenue"] for c in companies_list if c["revenue"] is not None and c["revenue"] > 0)
    companies_with_rev_count = sum(1 for c in companies_list if c["revenue"] is not None and c["revenue"] > 0)

    # Sector aggregations with de-duplicated / weighted company revenue allocation
    # To prevent multiplying company revenue when a vendor operates in multiple sectors
    comp_products_by_sec = defaultdict(lambda: defaultdict(int))
    comp_total_prods = defaultdict(int)
    for p in all_products:
        cid = int(p["companyId"])
        mid = str(p["macroSectorId"])
        comp_products_by_sec[cid][mid] += 1
        comp_total_prods[cid] += 1

    sec_weighted_rev: dict[str, float] = defaultdict(float)
    sec_active_companies: dict[str, set[int]] = defaultdict(set)
    sec_companies_with_rev: dict[str, set[int]] = defaultdict(set)

    for c in companies_list:
        cid = c["id"]
        c_rev = c["revenue"] or 0
        tot = comp_total_prods[cid]
        if tot == 0:
            continue
        for mid, count in comp_products_by_sec[cid].items():
            weight = count / tot
            if c_rev > 0:
                sec_weighted_rev[mid] += c_rev * weight
                sec_companies_with_rev[mid].add(cid)
            sec_active_companies[mid].add(cid)

    macro_aggregates: dict[str, dict[str, object]] = {}
    for spec in MACRO_SECTOR_SPECS:
        mid = spec["id"]
        prods = [p for p in all_products if p["macroSectorId"] == mid]
        hw_high = sum(1 for p in prods if p["hardwareDependency"]["level"] == "high")
        hw_med = sum(1 for p in prods if p["hardwareDependency"]["level"] == "medium")
        api_cnt = sum(1 for p in prods if p["apiConnectivity"]["hasApi"])
        public_pricing_cnt = sum(1 for p in prods if p["pricingModel"]["type"] == "public")
        trial_cnt = sum(1 for p in prods if p["pricingModel"]["type"] == "trial")

        macro_aggregates[mid] = {
            "id": mid,
            "name": spec["name"],
            "slug": spec["slug"],
            "description": spec["description"],
            "productCount": len(prods),
            "companyCount": len(sec_active_companies[mid]),
            "companiesWithRevenueCount": len(sec_companies_with_rev[mid]),
            "totalRevenue": round(sec_weighted_rev[mid], 0),
            "hwHighCount": hw_high,
            "hwMedCount": hw_med,
            "hwRate": round((hw_high + hw_med) / len(prods) * 100, 1) if prods else 0,
            "apiRate": round(api_cnt / len(prods) * 100, 1) if prods else 0,
            "publicPricingRate": round(public_pricing_cnt / len(prods) * 100, 1) if prods else 0,
            "trialRate": round(trial_cnt / len(prods) * 100, 1) if prods else 0,
        }

    # Device classes summary
    device_counter: dict[str, int] = {}
    for p in all_products:
        for d in p["hardwareDependency"]["devices"]:
            device_counter[d] = device_counter.get(d, 0) + 1
    device_summary = sorted([{"device": k, "count": v} for k, v in device_counter.items()], key=lambda x: x["count"], reverse=True)

    # Lock-in summary
    lock_high_cnt = sum(1 for p in all_products if p["lockIn"]["level"] == "high")
    lock_med_cnt = sum(1 for p in all_products if p["lockIn"]["level"] == "medium")
    lock_low_cnt = sum(1 for p in all_products if p["lockIn"]["level"] == "low")

    # Pricing summary
    price_pub_cnt = sum(1 for p in all_products if p["pricingModel"]["type"] == "public")
    price_trial_cnt = sum(1 for p in all_products if p["pricingModel"]["type"] == "trial")
    price_quote_cnt = sum(1 for p in all_products if p["pricingModel"]["type"] == "quote")
    price_undisc_cnt = sum(1 for p in all_products if p["pricingModel"]["type"] == "undisclosed")

    # Advanced BI: correlation between lock-in level and market signals
    lock_levels = [
        ("low", "Basso Lock-in (Aperto)"),
        ("medium", "Medio Lock-in (Standard)"),
        ("high", "Alto Lock-in (Ecosistema Chiuso)"),
    ]
    lockin_correlation = []
    for level, level_label in lock_levels:
        grp = [p for p in all_products if p["lockIn"]["level"] == level]
        n = len(grp)
        if n == 0:
            continue
        lockin_correlation.append({
            "level": level,
            "label": level_label,
            "count": n,
            "publicPricingRate": round(sum(1 for p in grp if p["pricingModel"]["type"] == "public") / n * 100, 1),
            "apiRate": round(sum(1 for p in grp if p["apiConnectivity"]["hasApi"]) / n * 100, 1),
            "hwRate": round(sum(1 for p in grp if p["hardwareDependency"]["level"] in ("high", "medium")) / n * 100, 1),
            "avgFeatures": round(sum(p["featureCount"] or 0 for p in grp) / n, 1),
            "avgTechnical": round(sum(p["technicalCount"] or 0 for p in grp) / n, 1),
        })

    # Advanced BI: revenue per employee (productivity proxy on observed financials)
    rev_per_emp = []
    for c in companies_list:
        if c["revenue"] and c["employees"] and c["revenue"] > 0 and c["employees"] >= 5:
            rev_per_emp.append({
                "name": c["name"],
                "group": c["group"],
                "website": c["website"],
                "revenue": c["revenue"],
                "revenueYear": c["revenueYear"],
                "employees": c["employees"],
                "employeesYear": c["employeesYear"],
                "ratio": round(c["revenue"] / c["employees"], 0),
                "products": len(c["products"]),
            })
    rev_per_emp.sort(key=lambda x: x["ratio"], reverse=True)
    ratios_sorted = sorted(x["ratio"] for x in rev_per_emp)
    avg_rev_per_emp = round(sum(ratios_sorted) / len(ratios_sorted), 0) if ratios_sorted else 0
    if ratios_sorted:
        mid = len(ratios_sorted) // 2
        median_rev_per_emp = ratios_sorted[mid] if len(ratios_sorted) % 2 else round((ratios_sorted[mid - 1] + ratios_sorted[mid]) / 2, 0)
    else:
        median_rev_per_emp = 0


    categories: dict[str, dict[str, object]] = {}
    for p in all_products:
        cat_slug = str(p["categorySlug"])
        cat_name = str(p["categoryName"])
        category = categories.setdefault(cat_slug, {"slug": cat_slug, "name": cat_name, "products": []})
        category["products"].append(p)

    payload = {
        "generatedAt": "2026-10",
        "productCount": len(all_products),
        "companyCount": len(company_dict),
        "revenueCoverage": companies_with_rev_count,
        "totalObservedRevenue": total_revenue_observed,
        "marketInsights": {
            "totalRevenue": total_revenue_observed,
            "companiesWithRevenue": companies_with_rev_count,
            "topCompaniesByRevenue": top_revenue_companies,
            "topCompaniesByEmployees": top_employee_companies,
            "macroSectors": list(macro_aggregates.values()),
            "hardwareMatrix": {
                "highCount": sum(1 for p in all_products if p["hardwareDependency"]["level"] == "high"),
                "mediumCount": sum(1 for p in all_products if p["hardwareDependency"]["level"] == "medium"),
                "noneCount": sum(1 for p in all_products if p["hardwareDependency"]["level"] == "none"),
                "devices": device_summary,
            },
            "lockInMatrix": {
                "highCount": lock_high_cnt,
                "mediumCount": lock_med_cnt,
                "lowCount": lock_low_cnt,
                "withApiCount": sum(1 for p in all_products if p["apiConnectivity"]["hasApi"]),
                "withoutApiCount": sum(1 for p in all_products if not p["apiConnectivity"]["hasApi"]),
            },
            "pricingTransparency": {
                "publicCount": price_pub_cnt,
                "trialCount": price_trial_cnt,
                "quoteCount": price_quote_cnt,
                "undisclosedCount": price_undisc_cnt,
            },
            "lockInCorrelation": lockin_correlation,
            "revenuePerEmployee": {
                "top": rev_per_emp[:15],
                "average": avg_rev_per_emp,
                "median": median_rev_per_emp,
                "sample": len(rev_per_emp),
            },
        },
        "macroSectors": list(macro_aggregates.values()),
        "categories": sorted(categories.values(), key=lambda item: (-len(item["products"]), item["name"])),
        "products": all_products,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "window.CATALOGUE_DATA = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    return len(all_products)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "catalog.sqlite")
    parser.add_argument("--output", type=Path, default=ROOT / "web" / "catalog-data.js")
    args = parser.parse_args()
    count = export_catalogue(args.database, args.output)
    print(f"Esportati {count} prodotti e analisi di mercato in {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
