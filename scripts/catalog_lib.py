"""Shared validation and import helpers for the local catalogue."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

SCHEMA_VERSION = "1.0"
CONFIDENCE = {"high", "medium", "low"}
ENTITY_TYPES = {"company", "group", "product"}
TERM_KINDS = {"category", "vertical", "segment", "deployment", "pricing_model"}
TECHNICAL_KINDS = {
    "deployment_model", "delivery_model", "client_platform", "mobile_platform",
    "api_protocol", "integration_standard", "database", "programming_language",
    "framework", "cloud_provider", "hosting_model", "authentication",
    "security_standard", "data_residency", "extensibility", "hardware_integration", "auditability",
}
SUPPORT_LEVELS = {"native", "addon", "integration", "planned", "unknown"}
SOURCE_TYPES = {
    "official_product_page", "official_company_page", "official_pricing_page",
    "annual_report", "company_register", "press_release", "news_article",
    "review_platform", "directory", "other",
}
METRICS = {"revenue", "ebitda", "net_income", "employees", "customers"}


class BundleError(ValueError):
    """A bundle cannot safely be imported."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return re.sub(r"(^-|-$)", "", re.sub(r"[^a-z0-9]+", "-", normalized)) or "item"


def is_iso_datetime(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def is_http_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def load_bundle(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BundleError(f"{path}: JSON non leggibile: {exc}") from exc
    if not isinstance(payload, dict):
        raise BundleError(f"{path}: il bundle deve essere un oggetto JSON")
    return payload


def paths_from_input(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
        return
    if not path.is_dir():
        raise BundleError(f"Percorso non trovato: {path}")
    yield from sorted(item for item in path.rglob("*.json") if item.is_file())


def _require(mapping: dict[str, Any], key: str, label: str, errors: list[str]) -> Any:
    value = mapping.get(key)
    if value is None or value == "":
        errors.append(f"{label}: campo obbligatorio '{key}' assente")
    return value


def validate_bundle(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if bundle.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version deve essere '{SCHEMA_VERSION}'")
    _require(bundle, "record_id", "bundle", errors)
    if not is_iso_datetime(bundle.get("created_at")):
        errors.append("bundle: 'created_at' deve essere ISO-8601")
    creator = bundle.get("created_by")
    if not isinstance(creator, dict) or not creator.get("agent_id"):
        errors.append("bundle: 'created_by.agent_id' è obbligatorio")

    entities = bundle.get("entities")
    sources = bundle.get("sources")
    if not isinstance(entities, list) or not entities:
        errors.append("bundle: 'entities' deve essere una lista non vuota")
        entities = []
    if not isinstance(sources, list) or not sources:
        errors.append("bundle: 'sources' deve essere una lista non vuota")
        sources = []

    entity_ids: set[str] = set()
    entity_types: dict[str, str] = {}
    for index, entity in enumerate(entities):
        label = f"entities[{index}]"
        if not isinstance(entity, dict):
            errors.append(f"{label}: deve essere un oggetto")
            continue
        local_id = _require(entity, "local_id", label, errors)
        entity_type = _require(entity, "entity_type", label, errors)
        _require(entity, "name", label, errors)
        if local_id in entity_ids:
            errors.append(f"{label}: local_id duplicato '{local_id}'")
        elif isinstance(local_id, str):
            entity_ids.add(local_id)
            entity_types[local_id] = entity_type
        if entity_type not in ENTITY_TYPES:
            errors.append(f"{label}: entity_type non supportato '{entity_type}'")
        if entity_type == "product":
            company_ref = entity.get("company_ref")
            if company_ref not in entity_ids and company_ref not in entity_types:
                errors.append(f"{label}: 'company_ref' deve riferirsi a una company precedente")
            elif entity_types.get(company_ref) != "company":
                errors.append(f"{label}: 'company_ref' deve riferirsi a una company")
        if entity_type == "company" and entity.get("group_ref"):
            if entity["group_ref"] not in entity_types or entity_types.get(entity["group_ref"]) != "group":
                errors.append(f"{label}: 'group_ref' deve riferirsi a un group precedente")

    source_ids: set[str] = set()
    for index, source in enumerate(sources):
        label = f"sources[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{label}: deve essere un oggetto")
            continue
        local_id = _require(source, "local_id", label, errors)
        if local_id in source_ids:
            errors.append(f"{label}: local_id duplicato '{local_id}'")
        elif isinstance(local_id, str):
            source_ids.add(local_id)
        if not is_http_url(source.get("url")):
            errors.append(f"{label}: 'url' deve essere HTTP(S)")
        if source.get("source_type") not in SOURCE_TYPES:
            errors.append(f"{label}: source_type non supportato")
        if not is_iso_datetime(source.get("accessed_at")):
            errors.append(f"{label}: 'accessed_at' deve essere ISO-8601")

    def check_subject(item: dict[str, Any], label: str) -> None:
        ref = item.get("subject_ref")
        if ref not in entity_types:
            errors.append(f"{label}: subject_ref inesistente '{ref}'")

    def check_source(item: dict[str, Any], label: str) -> None:
        ref = item.get("source_ref")
        if ref not in source_ids:
            errors.append(f"{label}: source_ref inesistente '{ref}'")

    for index, document in enumerate(bundle.get("documents", [])):
        label = f"documents[{index}]"
        if not isinstance(document, dict):
            errors.append(f"{label}: deve essere un oggetto")
            continue
        _require(document, "local_id", label, errors)
        check_source(document, label)
        if not isinstance(document.get("text"), str) or not document["text"].strip():
            errors.append(f"{label}: 'text' deve essere una stringa non vuota")

    for index, item in enumerate(bundle.get("classifications", [])):
        label = f"classifications[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label}: deve essere un oggetto")
            continue
        check_subject(item, label)
        check_source(item, label)
        if entity_types.get(item.get("subject_ref")) != "product":
            errors.append(f"{label}: una classificazione può riferirsi solo a un product")
        if item.get("kind") not in TERM_KINDS:
            errors.append(f"{label}: kind non supportato")
        _require(item, "term_slug", label, errors)
        _require(item, "term_name", label, errors)
        if item.get("confidence") not in CONFIDENCE:
            errors.append(f"{label}: confidence non supportata")

    for index, item in enumerate(bundle.get("features", [])):
        label = f"features[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label}: deve essere un oggetto")
            continue
        check_subject(item, label)
        check_source(item, label)
        if entity_types.get(item.get("subject_ref")) != "product":
            errors.append(f"{label}: una feature può riferirsi solo a un product")
        _require(item, "feature_slug", label, errors)
        _require(item, "feature_name", label, errors)
        if item.get("support_level") not in SUPPORT_LEVELS:
            errors.append(f"{label}: support_level non supportato")
        if item.get("confidence") not in CONFIDENCE:
            errors.append(f"{label}: confidence non supportata")

    for index, item in enumerate(bundle.get("technical_characteristics", [])):
        label = f"technical_characteristics[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label}: deve essere un oggetto")
            continue
        check_subject(item, label)
        check_source(item, label)
        if entity_types.get(item.get("subject_ref")) != "product":
            errors.append(f"{label}: una caratteristica tecnica può riferirsi solo a un product")
        if item.get("kind") not in TECHNICAL_KINDS:
            errors.append(f"{label}: kind non supportato")
        _require(item, "term_slug", label, errors)
        _require(item, "term_name", label, errors)
        if item.get("relationship_type") not in {"supports", "uses", "compatible_with", "certified_for", "available_as", "unknown"}:
            errors.append(f"{label}: relationship_type non supportato")
        if item.get("confidence") not in CONFIDENCE:
            errors.append(f"{label}: confidence non supportata")

    for index, item in enumerate(bundle.get("industry_classifications", [])):
        label = f"industry_classifications[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label}: deve essere un oggetto")
            continue
        company_ref = item.get("company_ref")
        if entity_types.get(company_ref) != "company":
            errors.append(f"{label}: company_ref deve riferirsi a una company")
        check_source(item, label)
        if item.get("classification_system", "ATECO") != "ATECO":
            errors.append(f"{label}: per ora è supportato solo il sistema ATECO")
        _require(item, "classification_version", label, errors)
        _require(item, "code", label, errors)
        if item.get("role") not in {"primary", "secondary"}:
            errors.append(f"{label}: role deve essere primary o secondary")

    for index, item in enumerate(bundle.get("financial_metrics", [])):
        label = f"financial_metrics[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label}: deve essere un oggetto")
            continue
        check_subject(item, label)
        check_source(item, label)
        if item.get("metric") not in METRICS:
            errors.append(f"{label}: metric non supportata")
        if not isinstance(item.get("period_year"), int):
            errors.append(f"{label}: period_year deve essere un intero")
        if item.get("value_kind") not in {"reported", "estimated", "derived"}:
            errors.append(f"{label}: value_kind non supportato")
        if item.get("confidence") not in CONFIDENCE:
            errors.append(f"{label}: confidence non supportata")
        value = item.get("value")
        if not isinstance(value, dict) or not any(key in value for key in ("exact", "min", "max")):
            errors.append(f"{label}: value deve contenere exact, min o max")

    for collection in ("facts", "claims", "notes"):
        for index, item in enumerate(bundle.get(collection, [])):
            label = f"{collection}[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{label}: deve essere un oggetto")
                continue
            check_subject(item, label)
            if collection != "notes":
                check_source(item, label)
            if collection == "facts":
                if item.get("value_kind") not in {"reported", "estimated", "derived", "observed"}:
                    errors.append(f"{label}: value_kind non supportato")
                if "value" not in item:
                    errors.append(f"{label}: value obbligatorio")
            if collection == "claims" and item.get("claim_type") not in {"observed", "inferred", "estimated"}:
                errors.append(f"{label}: claim_type non supportato")
            if collection == "notes":
                if item.get("note_type") not in {
                    "analyst_inference", "research_note", "data_quality", "source_quality", "classification_rationale"
                }:
                    errors.append(f"{label}: note_type non supportato")
                _require(item, "text", label, errors)
            if item.get("confidence") not in CONFIDENCE:
                errors.append(f"{label}: confidence non supportata")
    return errors


def bundle_hash(bundle: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(bundle).encode("utf-8")).hexdigest()
