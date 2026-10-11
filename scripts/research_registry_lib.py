"""Atomic URL/candidate coordination primitives shared by research scripts."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


ROOT = Path(__file__).resolve().parents[1]
TRACKING_PARAMETERS = {"gclid", "fbclid", "dclid", "msclkid", "ref", "ref_"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    return value.isoformat()


def canonicalize_url(url: str) -> str:
    parsed = urlsplit(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL deve essere HTTP(S) assoluto")
    host = parsed.hostname.lower() if parsed.hostname else ""
    port = parsed.port
    netloc = host if port is None or (parsed.scheme == "https" and port == 443) or (parsed.scheme == "http" and port == 80) else f"{host}:{port}"
    if parsed.username or parsed.password:
        raise ValueError("URL con credenziali non consentito")
    query = [
        (key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in TRACKING_PARAMETERS
    ]
    path = parsed.path or "/"
    return urlunsplit((parsed.scheme.lower(), netloc, path, urlencode(query, doseq=True), ""))


def target_key_for_url(url: str) -> str:
    return "url:" + hashlib.sha256(url.encode("utf-8")).hexdigest()


def candidate_key_for(name: str, company_name: str | None, vat_id: str | None, website: str | None) -> str:
    if vat_id:
        return "vat:" + "".join(character for character in vat_id if character.isdigit())
    identity = "|".join((name.strip().lower(), (company_name or "").strip().lower(), (website or "").strip().lower()))
    return "candidate:" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]


def ensure_registry(connection: sqlite3.Connection) -> None:
    exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='registry_meta'"
    ).fetchone()
    if exists:
        return
    schema = (ROOT / "schemas" / "002_research_registry.sql").read_text(encoding="utf-8")
    connection.executescript(schema)
    connection.execute("INSERT OR IGNORE INTO registry_meta(key, value) VALUES ('schema_version', '1')")
    connection.commit()


def connect(database: Path) -> sqlite3.Connection:
    database.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database, timeout=15, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA busy_timeout = 15000")
    ensure_registry(connection)
    return connection


def is_fresh(row: sqlite3.Row, now: datetime) -> bool:
    if row["status"] != "ready" or not row["refresh_after"]:
        return False
    try:
        return datetime.fromisoformat(row["refresh_after"].replace("Z", "+00:00")) > now
    except ValueError:
        return False


def reserve_url(connection: sqlite3.Connection, url: str, agent_id: str, purpose: str, lease_minutes: int) -> dict:
    canonical_url = canonicalize_url(url)
    now = utc_now()
    key = target_key_for_url(canonical_url)
    connection.execute("BEGIN IMMEDIATE")
    try:
        cache = connection.execute("SELECT * FROM source_cache WHERE canonical_url = ?", (canonical_url,)).fetchone()
        if cache and is_fresh(cache, now):
            connection.execute("COMMIT")
            return {"result": "cached", "canonical_url": canonical_url, "cache": dict(cache)}
        lease = connection.execute("SELECT * FROM research_leases WHERE target_key = ?", (key,)).fetchone()
        if lease:
            expires_at = datetime.fromisoformat(lease["expires_at"].replace("Z", "+00:00"))
            if expires_at > now and lease["agent_id"] != agent_id:
                connection.execute("COMMIT")
                return {"result": "busy", "canonical_url": canonical_url, "lease": dict(lease)}
        expiry = now + timedelta(minutes=lease_minutes)
        connection.execute(
            """INSERT INTO research_leases(target_key, target_kind, canonical_url, agent_id, purpose, leased_at, expires_at, updated_at)
               VALUES (?, 'url', ?, ?, ?, ?, ?, ?)
               ON CONFLICT(target_key) DO UPDATE SET agent_id=excluded.agent_id, purpose=excluded.purpose,
                leased_at=excluded.leased_at, expires_at=excluded.expires_at, updated_at=excluded.updated_at""",
            (key, canonical_url, agent_id, purpose, iso(now), iso(expiry), iso(now)),
        )
        connection.execute("COMMIT")
        return {"result": "leased", "canonical_url": canonical_url, "expires_at": iso(expiry)}
    except Exception:
        connection.execute("ROLLBACK")
        raise


def complete_url(connection: sqlite3.Connection, url: str, agent_id: str, status: str, metadata: dict) -> None:
    canonical_url = canonicalize_url(url)
    key = target_key_for_url(canonical_url)
    now = iso(utc_now())
    connection.execute("BEGIN IMMEDIATE")
    try:
        lease = connection.execute("SELECT agent_id FROM research_leases WHERE target_key = ?", (key,)).fetchone()
        if not lease or lease["agent_id"] != agent_id:
            raise ValueError("lease non posseduto da questo agente")
        columns = ["canonical_url", "status", "updated_at"]
        values: list[object] = [canonical_url, status, now]
        for name in (
            "last_fetch_at", "refresh_after", "http_status", "content_type", "byte_size", "content_hash",
            "etag", "last_modified", "retention", "rights_basis", "artifact_path", "extract_path", "source_id", "notes",
        ):
            if name in metadata:
                columns.append(name)
                values.append(metadata[name])
        assignments = ", ".join(f"{column}=excluded.{column}" for column in columns if column != "canonical_url")
        placeholders = ", ".join("?" for _ in columns)
        connection.execute(
            f"INSERT INTO source_cache({', '.join(columns)}) VALUES ({placeholders}) "
            f"ON CONFLICT(canonical_url) DO UPDATE SET {assignments}", values,
        )
        connection.execute("DELETE FROM research_leases WHERE target_key = ?", (key,))
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise


def release_url(connection: sqlite3.Connection, url: str, agent_id: str) -> bool:
    key = target_key_for_url(canonicalize_url(url))
    cursor = connection.execute("DELETE FROM research_leases WHERE target_key = ? AND agent_id = ?", (key, agent_id))
    return cursor.rowcount > 0


def add_candidate(
    connection: sqlite3.Connection, *, name: str, company_name: str | None, vat_id: str | None,
    website: str | None, discovery_source_url: str | None, discovery_method: str, priority: int,
    metadata: dict | None = None,
) -> dict:
    key = candidate_key_for(name, company_name, vat_id, website)
    now = iso(utc_now())
    connection.execute("BEGIN IMMEDIATE")
    try:
        if vat_id:
            existing = connection.execute("SELECT candidate_key FROM discovery_candidates WHERE vat_id = ?", (vat_id,)).fetchone()
            if existing:
                connection.execute("COMMIT")
                return {"result": "existing", "candidate_key": existing["candidate_key"]}
        existing = connection.execute("SELECT candidate_key FROM discovery_candidates WHERE candidate_key = ?", (key,)).fetchone()
        if existing:
            connection.execute("COMMIT")
            return {"result": "existing", "candidate_key": key}
        connection.execute(
            """INSERT INTO discovery_candidates(
                candidate_key, name, company_name, vat_id, website, discovery_source_url, discovery_method,
                priority, metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (key, name, company_name, vat_id, website, discovery_source_url, discovery_method, priority,
             json.dumps(metadata or {}, ensure_ascii=False, sort_keys=True), now, now),
        )
        connection.execute("COMMIT")
        return {"result": "added", "candidate_key": key}
    except Exception:
        connection.execute("ROLLBACK")
        raise


def claim_candidate(connection: sqlite3.Connection, candidate_key: str, agent_id: str, purpose: str, lease_minutes: int) -> dict:
    now = utc_now()
    lease_key = "candidate:" + candidate_key
    connection.execute("BEGIN IMMEDIATE")
    try:
        candidate = connection.execute("SELECT * FROM discovery_candidates WHERE candidate_key = ?", (candidate_key,)).fetchone()
        if not candidate:
            raise ValueError("candidato inesistente")
        if candidate["status"] not in {"new", "researching"}:
            connection.execute("COMMIT")
            return {"result": "unavailable", "status": candidate["status"], "candidate_key": candidate_key}
        lease = connection.execute("SELECT * FROM research_leases WHERE target_key = ?", (lease_key,)).fetchone()
        if lease and datetime.fromisoformat(lease["expires_at"].replace("Z", "+00:00")) > now and lease["agent_id"] != agent_id:
            connection.execute("COMMIT")
            return {"result": "busy", "candidate_key": candidate_key, "lease": dict(lease)}
        expiry = now + timedelta(minutes=lease_minutes)
        connection.execute(
            """INSERT INTO research_leases(target_key, target_kind, display_name, agent_id, purpose, leased_at, expires_at, updated_at)
               VALUES (?, 'candidate', ?, ?, ?, ?, ?, ?)
               ON CONFLICT(target_key) DO UPDATE SET agent_id=excluded.agent_id, purpose=excluded.purpose,
                leased_at=excluded.leased_at, expires_at=excluded.expires_at, updated_at=excluded.updated_at""",
            (lease_key, candidate["name"], agent_id, purpose, iso(now), iso(expiry), iso(now)),
        )
        connection.execute("UPDATE discovery_candidates SET status='researching', updated_at=? WHERE candidate_key=?", (iso(now), candidate_key))
        connection.execute("COMMIT")
        return {"result": "leased", "candidate_key": candidate_key, "expires_at": iso(expiry)}
    except Exception:
        connection.execute("ROLLBACK")
        raise


def claim_next_candidate(connection: sqlite3.Connection, agent_id: str, purpose: str, lease_minutes: int) -> dict:
    # Another worker can claim the top candidate between the SELECT and the lease transaction.
    # Retry a bounded number of times so workers distribute across the queue instead of idling.
    for _ in range(20):
        candidate = connection.execute(
            "SELECT candidate_key FROM discovery_candidates WHERE status='new' ORDER BY priority DESC, created_at LIMIT 1"
        ).fetchone()
        if not candidate:
            return {"result": "empty"}
        result = claim_candidate(connection, candidate["candidate_key"], agent_id, purpose, lease_minutes)
        if result["result"] != "busy":
            return result
    return {"result": "busy"}


def complete_candidate(connection: sqlite3.Connection, candidate_key: str, agent_id: str, status: str, duplicate_of: str | None = None) -> None:
    if status not in {"qualified", "rejected", "duplicate"}:
        raise ValueError("stato finale candidato non supportato")
    lease_key = "candidate:" + candidate_key
    connection.execute("BEGIN IMMEDIATE")
    try:
        lease = connection.execute("SELECT agent_id FROM research_leases WHERE target_key = ?", (lease_key,)).fetchone()
        if not lease or lease["agent_id"] != agent_id:
            raise ValueError("lease candidato non posseduto da questo agente")
        connection.execute(
            "UPDATE discovery_candidates SET status=?, duplicate_of=?, updated_at=? WHERE candidate_key=?",
            (status, duplicate_of, iso(utc_now()), candidate_key),
        )
        connection.execute("DELETE FROM research_leases WHERE target_key = ?", (lease_key,))
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise
