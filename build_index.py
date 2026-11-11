#!/usr/bin/env python3
"""
Merges output_funds/fund_*.json into:
  - archive_full.json   : full nested fond -> opisi -> dela structure
  - search_index.jsonl  : one flat JSON line per delo (or per opis, if dela
                           weren't fetched), for fast line-by-line searching
                           without loading everything into memory.

Run after scrape_archive.py has produced at least some fund_*.json files.
Safe to re-run any time to refresh the merged files with newly-scraped fonds.
"""

import json
from pathlib import Path

OUTPUT_DIR = Path("output_funds")


def main():
    fund_files = sorted(OUTPUT_DIR.glob("fund_*.json"))
    print(f"Found {len(fund_files)} fond files to merge.")

    full = []
    index_lines = []

    for path in fund_files:
        with open(path, encoding="utf-8") as f:
            fund = json.load(f)
        full.append(fund)

        fund_label = f"{fund.get('number', '')} - {fund.get('title', '')}"
        for op in fund.get("opisi", []):
            op_label = f"{op.get('number', '')} - {op.get('title', '')}"
            dela = op.get("dela")
            if dela:
                for de in dela:
                    index_lines.append({
                        "fund_id": fund["id"],
                        "fund_number": fund.get("number", ""),
                        "fund_title": fund.get("title", ""),
                        "opis_id": op["id"],
                        "opis_number": op.get("number", ""),
                        "opis_title": op.get("title", ""),
                        "delo_id": de["id"],
                        "delo_number": de.get("number", ""),
                        "delo_title": de.get("title", ""),
                        "date_start": de.get("date_start", ""),
                        "date_end": de.get("date_end", ""),
                        "search_text": " ".join([
                            fund.get("title", ""), op.get("title", ""), de.get("title", "")
                        ]).lower(),
                    })
            else:
                # dela not fetched for this opis - still index at opis level
                index_lines.append({
                    "fund_id": fund["id"],
                    "fund_number": fund.get("number", ""),
                    "fund_title": fund.get("title", ""),
                    "opis_id": op["id"],
                    "opis_number": op.get("number", ""),
                    "opis_title": op.get("title", ""),
                    "delo_id": None,
                    "delo_number": None,
                    "delo_title": None,
                    "date_start": op.get("date_start", ""),
                    "date_end": op.get("date_end", ""),
                    "search_text": " ".join([
                        fund.get("title", ""), op.get("title", "")
                    ]).lower(),
                })

    with open("archive_full.json", "w", encoding="utf-8") as f:
        json.dump(full, f, ensure_ascii=False, indent=2)
    print(f"Wrote archive_full.json ({len(full)} fonds)")

    with open("search_index.jsonl", "w", encoding="utf-8") as f:
        for row in index_lines:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote search_index.jsonl ({len(index_lines)} rows)")


if __name__ == "__main__":
    main()
