#!/usr/bin/env python3
"""Fetch one public source safely after acquiring a registry lease.

This tool never executes or renders downloaded content. PDFs are treated as opaque files;
automatic text extraction is deliberately limited to HTML/text responses.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import ipaddress
import json
import socket
import sys
from datetime import timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from research_registry_lib import canonicalize_url, complete_url, connect, iso, reserve_url, utc_now


ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES_DEFAULT = 15 * 1024 * 1024
ALLOWED_RETENTIONS = {"metadata", "excerpt", "artifact"}
ALLOWED_RIGHTS = {"publicly_available", "permission", "public_domain", "internal"}


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg", "canvas"}:
            self.ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg", "canvas"} and self.ignored_depth:
            self.ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.ignored_depth and data.strip():
            self.parts.append(data.strip())

    def text(self) -> str:
        return "\n".join(self.parts)


def assert_public_url(url: str) -> None:
    parsed = urlsplit(url)
    hostname = parsed.hostname
    if not hostname or hostname.lower() == "localhost" or hostname.lower().endswith(".local"):
        raise ValueError("host locale/non pubblico rifiutato")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)}
    except socket.gaierror as exc:
        raise ValueError(f"DNS non risolvibile: {exc}") from exc
    if not addresses:
        raise ValueError("host senza indirizzi pubblici")
    for address in addresses:
        if not ipaddress.ip_address(address).is_global:
            raise ValueError("host con indirizzo privato/riservato rifiutato")


class PublicRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        if code not in {301, 302, 303, 307, 308}:
            return None
        assert_public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def read_limited(response, max_bytes: int) -> bytes:  # type: ignore[no-untyped-def]
    declared = response.headers.get("Content-Length")
    if declared and int(declared) > max_bytes:
        raise ValueError(f"contenuto oltre il limite di {max_bytes} byte")
    body = bytearray()
    while True:
        block = response.read(min(64 * 1024, max_bytes + 1 - len(body)))
        if not block:
            return bytes(body)
        body.extend(block)
        if len(body) > max_bytes:
            raise ValueError(f"contenuto oltre il limite di {max_bytes} byte")


def detect_kind(body: bytes, content_type: str) -> str:
    lowered = content_type.lower().split(";", 1)[0].strip()
    if body.startswith(b"%PDF-"):
        return "pdf"
    if body.startswith((b"PK\x03\x04", b"MZ")):
        raise ValueError("archivio o eseguibile rifiutato")
    if lowered in {"text/html", "application/xhtml+xml"} or b"<html" in body[:1024].lower():
        return "html"
    if lowered.startswith("text/"):
        return "text"
    raise ValueError(f"MIME non consentito: {content_type or 'assente'}")


def decoded_text(body: bytes, kind: str, content_type: str) -> str | None:
    if kind == "pdf":
        return None
    charset = "utf-8"
    for piece in content_type.split(";")[1:]:
        if piece.strip().lower().startswith("charset="):
            charset = piece.split("=", 1)[1].strip().strip('"')
    text = body.decode(charset, errors="replace")
    if kind == "html":
        parser = TextExtractor()
        parser.feed(text)
        return html.unescape(parser.text())
    return text


def write_content(path: Path, content: bytes | str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, str):
        path.write_text(content, encoding="utf-8")
    else:
        path.write_bytes(content)
    return str(path.relative_to(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--agent", required=True)
    parser.add_argument("--purpose", required=True)
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "research-state.sqlite")
    parser.add_argument("--retention", choices=sorted(ALLOWED_RETENTIONS), default="metadata")
    parser.add_argument("--rights-basis", choices=sorted(ALLOWED_RIGHTS))
    parser.add_argument("--max-bytes", type=int, default=MAX_BYTES_DEFAULT)
    parser.add_argument("--refresh-hours", type=int, default=24 * 30)
    args = parser.parse_args()
    if args.max_bytes < 1024 or args.max_bytes > 100 * 1024 * 1024:
        parser.error("--max-bytes deve essere tra 1 KiB e 100 MiB")
    if args.refresh_hours < 1:
        parser.error("--refresh-hours deve essere positivo")
    if args.retention == "artifact" and not args.rights_basis:
        parser.error("--retention artifact richiede --rights-basis esplicito")

    connection = connect(args.database)
    lease_held = False
    try:
        result = reserve_url(connection, args.url, args.agent, args.purpose, lease_minutes=30)
        if result["result"] != "leased":
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            return 3 if result["result"] == "busy" else 0
        lease_held = True
        url = result["canonical_url"]
        assert_public_url(url)
        request = Request(url, headers={
            "User-Agent": "MappaGestionaliResearch/0.1 (+local-catalogue; no-cookies)",
            "Accept": "text/html,application/xhtml+xml,text/plain,application/pdf;q=0.9,*/*;q=0.1",
        })
        opener = build_opener(PublicRedirectHandler())
        with opener.open(request, timeout=20) as response:
            final_url = canonicalize_url(response.geturl())
            assert_public_url(final_url)
            body = read_limited(response, args.max_bytes)
            content_type = response.headers.get("Content-Type", "")
            kind = detect_kind(body, content_type)
            text = decoded_text(body, kind, content_type)
            digest = hashlib.sha256(body).hexdigest()
            artifact_path = extract_path = None
            if args.retention == "artifact":
                extension = {"pdf": "pdf", "html": "html", "text": "txt"}[kind]
                artifact_path = write_content(ROOT / "data" / "artifacts" / digest[:2] / f"{digest}.{extension}", body)
            elif args.retention == "excerpt" and text is not None:
                extract_path = write_content(ROOT / "data" / "extracts" / digest[:2] / f"{digest}.txt", text)
            now = utc_now()
            metadata = {
                "last_fetch_at": iso(now),
                "refresh_after": iso(now + timedelta(hours=args.refresh_hours)),
                "http_status": response.status,
                "content_type": content_type,
                "byte_size": len(body),
                "content_hash": f"sha256:{digest}",
                "etag": response.headers.get("ETag"),
                "last_modified": response.headers.get("Last-Modified"),
                "retention": args.retention,
                "rights_basis": args.rights_basis,
                "artifact_path": artifact_path,
                "extract_path": extract_path,
                "notes": f"final_url={final_url}; kind={kind}; no execution or rendering performed",
            }
            complete_url(connection, url, args.agent, "ready", metadata)
            lease_held = False
            print(json.dumps({"result": "fetched", "url": url, "final_url": final_url, "kind": kind, **metadata}, ensure_ascii=False, sort_keys=True))
            return 0
    except (HTTPError, URLError, OSError, ValueError) as exc:
        if lease_held:
            try:
                complete_url(connection, args.url, args.agent, "failed", {"notes": str(exc)})
                lease_held = False
            except ValueError:
                pass
        print(f"ERRORE: {exc}", file=sys.stderr)
        return 2
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
