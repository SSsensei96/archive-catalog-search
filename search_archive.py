#!/usr/bin/env python3
"""
Quick keyword search over search_index.jsonl (built by build_index.py).

USAGE
    python search_archive.py "целина"
    python search_archive.py "целина" "1954"      # all terms must match (AND)
    python search_archive.py --any "нефть" "газ"   # any term matches (OR)
    python search_archive.py "целина" --limit 50
"""

import argparse
import json
import sys
from pathlib import Path


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("terms", nargs="+", help="search term(s), case-insensitive")
    ap.add_argument("--any", action="store_true",
                     help="match if ANY term is present (default: ALL terms, AND)")
    ap.add_argument("--limit", type=int, default=100, help="max results to show")
    ap.add_argument("--index", default="search_index.jsonl", help="path to index file")
    args = ap.parse_args()

    idx_path = Path(args.index)
    if not idx_path.exists():
        print(f"'{args.index}' not found. Run build_index.py first.")
        return

    terms = [t.lower() for t in args.terms]
    matcher = any if args.any else all

    shown = 0
    total_checked = 0
    with open(idx_path, encoding="utf-8") as f:
        for line in f:
            total_checked += 1
            row = json.loads(line)
            text = row.get("search_text", "")
            if matcher(t in text for t in terms):
                shown += 1
                print("-" * 70)
                print(f"Fond {row['fund_number']}: {row['fund_title']}")
                print(f"  Opis {row['opis_number']}: {row['opis_title']}")
                if row.get("delo_id"):
                    print(f"    Delo {row['delo_number']}: {row['delo_title']}")
                print(f"  Dates: {row.get('date_start','')} - {row.get('date_end','')}")
                if shown >= args.limit:
                    print(f"\n(stopped at --limit {args.limit}; more results may exist)")
                    break

    print(f"\n{shown} match(es) shown, out of {total_checked} indexed entries checked.")


if __name__ == "__main__":
    main()
