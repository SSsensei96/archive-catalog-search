#!/usr/bin/env python3
"""
Scraper for the electronic catalog of the Archive of the President of
the Republic of Kazakhstan (archive.president.kz/ru/funds/ecatalog/).

Crawls the three-level hierarchy: Fond (фонд) -> Opis (опись) -> Delo (дело),
and writes one JSON file per fond to output_funds/, so the crawl can be
safely interrupted (Ctrl+C) and resumed later without losing progress or
re-fetching completed fonds.

USAGE
-----
    pip install -r requirements.txt

    # Full crawl (fonds + opisi + dela) - can take a few hours
    python scrape_archive.py

    # Only fonds + opisi, skip individual dela (fast, good first pass)
    python scrape_archive.py --skip-dela

    # Test on a handful of fonds first
    python scrape_archive.py --limit 5

    # Resume is automatic - just re-run the same command; fonds that
    # already have output_funds/fund_<id>.json are skipped.

Then run:
    python search_archive.py "your search term"

NOTES
-----
- This site's robots.txt disallows automated crawling. This script is
  intended for personal research use on public catalog metadata (titles
  and dates only, not scanned documents). Please keep the delay/worker
  settings reasonably polite - the defaults are deliberately conservative.
- Being a Bitrix site, it occasionally returns transient errors; the
  script retries with backoff and just logs+skips anything that
  ultimately fails, so you can re-run later to patch gaps.
"""

import argparse
import json
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://archive.president.kz/ru/funds/ecatalog/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; personal-research-archive-crawler/1.0)"
    )
}

OUTPUT_DIR = Path("output_funds")
FAILED_LOG = Path("failed_requests.log")

session = requests.Session()
session.headers.update(HEADERS)


# --------------------------------------------------------------------------
# HTTP + parsing helpers
# --------------------------------------------------------------------------

def fetch(params, retries=4, base_delay=1.5, timeout=30):
    """GET the catalog page with given query params, with retry/backoff."""
    last_err = None
    for attempt in range(retries):
        try:
            resp = session.get(BASE_URL, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            last_err = e
            wait = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
            time.sleep(wait)
    with open(FAILED_LOG, "a", encoding="utf-8") as f:
        f.write(f"{params} -> {last_err}\n")
    return None


def get_max_page(soup, container_id, pagen_key):
    """Find the highest PAGEN_x=page-N link inside a tab's pagination block."""
    container = soup.find(id=container_id)
    if not container:
        return 1
    pag = container.find(class_="bx-pagination")
    if not pag:
        return 1
    max_page = 1
    pattern = re.compile(rf"{pagen_key}=page-(\d+)")
    for a in pag.find_all("a", href=True):
        m = pattern.search(a["href"])
        if m:
            max_page = max(max_page, int(m.group(1)))
    return max_page


def parse_rows(soup, container_id, row_class, field_names):
    """Parse <tr class="row_class" data-id="..."><td>...</td>x4</tr> rows."""
    container = soup.find(id=container_id)
    if not container:
        return []
    out = []
    for tr in container.find_all("tr", class_=row_class):
        tds = tr.find_all("td")
        if len(tds) < 4:
            continue
        row = {"id": tr.get("data-id", "")}
        for name, td in zip(field_names, tds):
            row[name] = td.get_text(strip=True)
        out.append(row)
    return out


FIELDS = ["number", "title", "date_start", "date_end"]


# --------------------------------------------------------------------------
# Level fetchers
# --------------------------------------------------------------------------

def get_fonds_page(page_num):
    params = {}
    if page_num > 1:
        params["PAGEN_1"] = f"page-{page_num}"
    html = fetch(params)
    if not html:
        return [], 1
    soup = BeautifulSoup(html, "html.parser")
    fonds = parse_rows(soup, "pills-fonds", "fund", FIELDS)
    max_page = get_max_page(soup, "pills-fonds", "PAGEN_1")
    return fonds, max_page


def get_all_fonds(delay):
    """Paginate through the full fonds list."""
    all_fonds, page, max_page = [], 1, 1
    while True:
        fonds, max_page = get_fonds_page(page)
        all_fonds.extend(fonds)
        print(f"  fonds page {page}/{max_page}: +{len(fonds)} (total {len(all_fonds)})")
        if page >= max_page:
            break
        page += 1
        time.sleep(delay + random.uniform(0, 0.3))
    return all_fonds


def get_opisi_for_fund(fund_id, delay):
    all_opisi, page = [], 1
    while True:
        params = {"FUND": fund_id}
        if page > 1:
            params["PAGEN_2"] = f"page-{page}"
        html = fetch(params)
        if not html:
            break
        soup = BeautifulSoup(html, "html.parser")
        opisi = parse_rows(soup, "pills-opisi", "inventory", FIELDS)
        all_opisi.extend(opisi)
        max_page = get_max_page(soup, "pills-opisi", "PAGEN_2")
        if page >= max_page:
            break
        page += 1
        time.sleep(delay + random.uniform(0, 0.3))
    return all_opisi


def get_dela_for_opis(fund_id, opis_id, delay):
    all_dela, page = [], 1
    while True:
        params = {"FUND": fund_id, "INVENTORY": opis_id}
        if page > 1:
            params["PAGEN_3"] = f"page-{page}"
        html = fetch(params)
        if not html:
            break
        soup = BeautifulSoup(html, "html.parser")
        dela = parse_rows(soup, "pills-dela", "affair", FIELDS)
        all_dela.extend(dela)
        max_page = get_max_page(soup, "pills-dela", "PAGEN_3")
        if page >= max_page:
            break
        page += 1
        time.sleep(delay + random.uniform(0, 0.3))
    return all_dela


# --------------------------------------------------------------------------
# Per-fond worker (runs in a thread)
# --------------------------------------------------------------------------

def process_fund(fund, delay, skip_dela):
    fund_id = fund["id"]
    out_path = OUTPUT_DIR / f"fund_{fund_id}.json"
    if out_path.exists():
        return fund_id, "skipped (already done)"

    opisi = get_opisi_for_fund(fund_id, delay)
    print(f"  fond {fund_id}: found {len(opisi)} opisi "
          f"{[o['id'] for o in opisi]}")
    if not skip_dela:
        for op in opisi:
            op["dela"] = get_dela_for_opis(fund_id, op["id"], delay)
            print(f"    opis {op['id']} ({op.get('title','')[:40]}): "
                  f"{len(op['dela'])} dela")
    else:
        for op in opisi:
            op["dela"] = None  # not fetched this run

    record = dict(fund)
    record["opisi"] = opisi

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    n_dela = sum(len(op["dela"] or []) for op in opisi)
    return fund_id, f"{len(opisi)} opisi, {n_dela} dela"


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Crawl archive.president.kz e-catalog")
    ap.add_argument("--delay", type=float, default=0.6,
                     help="base delay in seconds between requests (default 0.6)")
    ap.add_argument("--workers", type=int, default=3,
                     help="number of fonds processed concurrently (default 3)")
    ap.add_argument("--limit", type=int, default=None,
                     help="only process the first N fonds (for testing)")
    ap.add_argument("--fund-ids", type=str, default=None,
                     help="comma-separated list of specific fund INTERNAL IDs (data-id) "
                          "to process, e.g. '139' or '139,5,7'. NOTE: this is the "
                          "internal database id, which can differ from the displayed "
                          "'№ фонда' catalog number. If you're targeting a fond by the "
                          "number you saw on the website, use --fund-numbers instead.")
    ap.add_argument("--fund-numbers", type=str, default=None,
                     help="comma-separated list of DISPLAYED fond numbers (the '№ фонда' "
                          "column, e.g. '139' or '5Н') to process - use this if you're "
                          "targeting a fond by what you saw in the browser")
    ap.add_argument("--skip-dela", action="store_true",
                     help="only fetch fonds + opisi, skip individual dela (much faster)")
    args = ap.parse_args()

    OUTPUT_DIR.mkdir(exist_ok=True)

    print("Fetching full list of fonds...")
    fonds = get_all_fonds(args.delay)
    print(f"Total fonds found: {len(fonds)}")

    if args.fund_ids:
        wanted = {x.strip() for x in args.fund_ids.split(",") if x.strip()}
        matched = [f for f in fonds if f["id"] in wanted]
        missing = wanted - {f["id"] for f in matched}
        if missing:
            print(f"WARNING: fund internal id(s) not found in listing: {sorted(missing)}")
        fonds = matched
        print(f"--fund-ids set: processing only {len(fonds)} matching fond(s) "
              f"{[(f['id'], f['number']) for f in fonds]}")

    if args.fund_numbers:
        wanted = {x.strip() for x in args.fund_numbers.split(",") if x.strip()}
        matched = [f for f in fonds if f["number"] in wanted]
        missing = wanted - {f["number"] for f in matched}
        if missing:
            print(f"WARNING: displayed fond number(s) not found in listing: {sorted(missing)}")
        fonds = matched
        print(f"--fund-numbers set: processing only {len(fonds)} matching fond(s) "
              f"{[(f['id'], f['number']) for f in fonds]}")

    if args.limit:
        fonds = fonds[: args.limit]
        print(f"--limit set: processing only {len(fonds)} fonds")

    todo = [f for f in fonds if not (OUTPUT_DIR / f"fund_{f['id']}.json").exists()]
    print(f"{len(fonds) - len(todo)} fonds already done, {len(todo)} remaining")

    done_count = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {
            ex.submit(process_fund, f, args.delay, args.skip_dela): f
            for f in todo
        }
        for fut in as_completed(futures):
            fund = futures[fut]
            try:
                fund_id, status = fut.result()
                done_count += 1
                print(f"[{done_count}/{len(todo)}] fond {fund_id} "
                      f"({fund.get('title', '')[:50]}): {status}")
            except Exception as e:
                print(f"[{done_count}/{len(todo)}] fond {fund.get('id')} FAILED: {e}")

    print("\nDone. Per-fond JSON files are in output_funds/.")
    print("Run build_index.py (or search_archive.py directly) next.")


if __name__ == "__main__":
    main()
