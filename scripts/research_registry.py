#!/usr/bin/env python3
"""Coordinate agents so a URL is fetched once and reused from local cache."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from research_registry_lib import (
    add_candidate, claim_candidate, claim_next_candidate, complete_candidate,
    complete_url, connect, release_url, reserve_url,
)


ROOT = Path(__file__).resolve().parents[1]


def emit(value: dict) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "research-state.sqlite")
    commands = parser.add_subparsers(dest="command", required=True)
    reserve = commands.add_parser("reserve", help="lease a URL or return a fresh cached result")
    reserve.add_argument("--url", required=True)
    reserve.add_argument("--agent", required=True)
    reserve.add_argument("--purpose", required=True)
    reserve.add_argument("--lease-minutes", type=int, default=30)
    complete = commands.add_parser("complete", help="store fetch metadata and release a held lease")
    complete.add_argument("--url", required=True)
    complete.add_argument("--agent", required=True)
    complete.add_argument("--status", choices=("ready", "failed", "blocked", "not_found"), required=True)
    complete.add_argument("--metadata-json", default="{}")
    release = commands.add_parser("release", help="release an unfinished lease")
    release.add_argument("--url", required=True)
    release.add_argument("--agent", required=True)
    candidate_add = commands.add_parser("candidate-add", help="add a discovery candidate with deterministic deduplication")
    candidate_add.add_argument("--name", required=True)
    candidate_add.add_argument("--company")
    candidate_add.add_argument("--vat-id")
    candidate_add.add_argument("--website")
    candidate_add.add_argument("--discovery-url")
    candidate_add.add_argument("--method", required=True)
    candidate_add.add_argument("--priority", type=int, default=50)
    candidate_add.add_argument("--metadata-json", default="{}")
    candidate_claim = commands.add_parser("candidate-claim", help="lease one known candidate")
    candidate_claim.add_argument("--candidate-key", required=True)
    candidate_claim.add_argument("--agent", required=True)
    candidate_claim.add_argument("--purpose", required=True)
    candidate_claim.add_argument("--lease-minutes", type=int, default=90)
    candidate_next = commands.add_parser("candidate-claim-next", help="lease the highest-priority new candidate")
    candidate_next.add_argument("--agent", required=True)
    candidate_next.add_argument("--purpose", required=True)
    candidate_next.add_argument("--lease-minutes", type=int, default=90)
    candidate_complete = commands.add_parser("candidate-complete", help="finish a held candidate lease")
    candidate_complete.add_argument("--candidate-key", required=True)
    candidate_complete.add_argument("--agent", required=True)
    candidate_complete.add_argument("--status", choices=("qualified", "rejected", "duplicate"), required=True)
    candidate_complete.add_argument("--duplicate-of")
    args = parser.parse_args()
    connection = connect(args.database)
    try:
        if args.command == "reserve":
            if args.lease_minutes < 1 or args.lease_minutes > 240:
                parser.error("--lease-minutes deve essere tra 1 e 240")
            result = reserve_url(connection, args.url, args.agent, args.purpose, args.lease_minutes)
            emit(result)
            return 3 if result["result"] == "busy" else 0
        if args.command == "complete":
            metadata = json.loads(args.metadata_json)
            if not isinstance(metadata, dict):
                parser.error("--metadata-json deve essere un oggetto JSON")
            complete_url(connection, args.url, args.agent, args.status, metadata)
            emit({"result": "completed"})
            return 0
        if args.command == "candidate-add":
            if not 0 <= args.priority <= 100:
                parser.error("--priority deve essere tra 0 e 100")
            metadata = json.loads(args.metadata_json)
            if not isinstance(metadata, dict):
                parser.error("--metadata-json deve essere un oggetto JSON")
            emit(add_candidate(connection, name=args.name, company_name=args.company, vat_id=args.vat_id,
                               website=args.website, discovery_source_url=args.discovery_url,
                               discovery_method=args.method, priority=args.priority, metadata=metadata))
            return 0
        if args.command in {"candidate-claim", "candidate-claim-next"}:
            if not 1 <= args.lease_minutes <= 480:
                parser.error("--lease-minutes deve essere tra 1 e 480")
            result = (claim_candidate(connection, args.candidate_key, args.agent, args.purpose, args.lease_minutes)
                      if args.command == "candidate-claim"
                      else claim_next_candidate(connection, args.agent, args.purpose, args.lease_minutes))
            emit(result)
            return 3 if result["result"] == "busy" else 0
        if args.command == "candidate-complete":
            complete_candidate(connection, args.candidate_key, args.agent, args.status, args.duplicate_of)
            emit({"result": "completed"})
            return 0
        released = release_url(connection, args.url, args.agent)
        emit({"result": "released" if released else "not_held"})
        return 0
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"ERRORE: {exc}")
        return 2
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
