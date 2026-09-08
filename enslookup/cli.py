"""command line entry point: enslookup <name or address> [...]"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from concurrent.futures import ThreadPoolExecutor

from . import __version__
from .ens import TEXT_KEYS_ALL, TEXT_KEYS_DEFAULT, Ens, Lookup
from .rpc import Rpc, RpcError, RpcUnavailable


def read_batch(path: str) -> list[str]:
    stream = sys.stdin if path == "-" else open(path, encoding="utf-8")
    with stream:
        return [line.strip() for line in stream if line.strip() and not line.startswith("#")]


def render(result: Lookup) -> str:
    lines = [result.query]
    if result.error:
        lines.append(f"  error     {result.error}")
        return "\n".join(lines)
    if result.name and result.kind == "address":
        tag = "  (unverified: the name does not point back to this address)" if result.verified is False else ""
        lines.append(f"  name      {result.name}{tag}")
    if result.address and result.kind == "name":
        lines.append(f"  address   {result.address}")
    if result.resolver:
        lines.append(f"  resolver  {result.resolver}")
    for key, value in result.text.items():
        lines.append(f"  {key:<9} {value}")
    if not result.resolved:
        lines.append("  (no reverse record)" if result.kind == "address" else "  (nothing found: no resolver or no address record)")
    return "\n".join(lines)


def safe_lookup(ens: Ens, query: str, keys: tuple[str, ...]) -> Lookup:
    try:
        return ens.lookup(query, keys)
    except (RpcError, RpcUnavailable) as exc:
        return Lookup(query=query, error=str(exc))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="enslookup", description="ens names to addresses and back, plus text records.")
    ap.add_argument("queries", nargs="*", help="names (vitalik.eth) or addresses (0x...)")
    ap.add_argument("--batch", metavar="FILE", help="one query per line, - for stdin")
    ap.add_argument("--text", metavar="KEYS", default=",".join(TEXT_KEYS_DEFAULT),
                    help=f"comma separated text record keys (default: {','.join(TEXT_KEYS_DEFAULT)})")
    ap.add_argument("--all-text", action="store_true", help=f"look up {', '.join(TEXT_KEYS_ALL)}")
    ap.add_argument("--no-text", action="store_true", help="addresses and names only")
    ap.add_argument("--json", action="store_true", help="json lines, one object per query")
    ap.add_argument("--csv", action="store_true", help="csv with a header row")
    ap.add_argument("--rpc", action="append", metavar="URL", help="json-rpc endpoint (repeatable, tried in order)")
    ap.add_argument("--workers", type=int, default=4, help="parallel lookups for batches (default 4)")
    ap.add_argument("--version", action="version", version=f"enslookup {__version__}")
    args = ap.parse_args(argv)

    queries = list(args.queries)
    if args.batch:
        queries += read_batch(args.batch)
    if not queries:
        ap.print_usage()
        return 2
    keys: tuple[str, ...] = () if args.no_text else TEXT_KEYS_ALL if args.all_text else tuple(
        k.strip() for k in args.text.split(",") if k.strip())

    ens = Ens(Rpc(args.rpc) if args.rpc else Rpc())
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        results = list(pool.map(lambda q: safe_lookup(ens, q, keys), queries))
    if all(r.error for r in results):
        print(f"error: {results[0].error}", file=sys.stderr)
        return 2

    if args.json:
        for r in results:
            print(json.dumps(r.as_dict(), ensure_ascii=False))
    elif args.csv:
        writer = csv.writer(sys.stdout, lineterminator="\n")
        writer.writerow(["query", "name", "address", "verified", *keys])
        for r in results:
            writer.writerow([r.query, r.name or "", r.address or "", "" if r.verified is None else str(r.verified).lower(),
                             *[r.text.get(k, "") for k in keys]])
    else:
        print("\n\n".join(render(r) for r in results))
    return 0 if any(r.resolved for r in results) else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
