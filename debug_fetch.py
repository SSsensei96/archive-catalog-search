#!/usr/bin/env python3
"""
Diagnostic tool: fetches ONE specific catalog query and shows exactly what
the server returned, so we can debug why parsing might be missing rows.

USAGE
    # See what fond listing page 1 looks like
    python debug_fetch.py

    # See the opisi for a given fond (by internal data-id)
    python debug_fetch.py --fund 139

    # See the dela for a given fond+opis combo
    python debug_fetch.py --fund 139 --inventory 201

Always saves the full raw HTML response to debug_response.html so you can
open it in a browser or a text editor and inspect it directly, and prints
a summary of what the parser was able to find in it.
"""

import argparse
from bs4 import BeautifulSoup

from scrape_archive import fetch, parse_rows, get_max_page, FIELDS, BASE_URL


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fund", type=str, default=None, help="internal fund data-id")
    ap.add_argument("--inventory", type=str, default=None, help="internal opis data-id")
    ap.add_argument("--page1", type=int, default=None, help="PAGEN_1 (fonds) page")
    ap.add_argument("--page2", type=int, default=None, help="PAGEN_2 (opisi) page")
    ap.add_argument("--page3", type=int, default=None, help="PAGEN_3 (dela) page")
    args = ap.parse_args()

    params = {}
    if args.fund:
        params["FUND"] = args.fund
    if args.inventory:
        params["INVENTORY"] = args.inventory
    if args.page1:
        params["PAGEN_1"] = f"page-{args.page1}"
    if args.page2:
        params["PAGEN_2"] = f"page-{args.page2}"
    if args.page3:
        params["PAGEN_3"] = f"page-{args.page3}"

    print(f"Requesting {BASE_URL} with params: {params}")
    html = fetch(params)
    if not html:
        print("FAILED to fetch (see failed_requests.log)")
        return

    with open("debug_response.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved raw response ({len(html)} chars) to debug_response.html\n")

    soup = BeautifulSoup(html, "html.parser")

    for container_id, row_class, pagen_key in [
        ("pills-fonds", "fund", "PAGEN_1"),
        ("pills-opisi", "inventory", "PAGEN_2"),
        ("pills-dela", "affair", "PAGEN_3"),
    ]:
        container = soup.find(id=container_id)
        print(f"--- {container_id} ---")
        if not container:
            print(f"  ! div id='{container_id}' NOT FOUND in response")
            continue
        rows = parse_rows(soup, container_id, row_class, FIELDS)
        max_page = get_max_page(soup, container_id, pagen_key)
        print(f"  rows found (class='{row_class}'): {len(rows)}")
        print(f"  max page ({pagen_key}): {max_page}")
        if rows:
            print(f"  first row: {rows[0]}")
        # Show any tr classes present, in case the real class name differs
        all_trs = container.find_all("tr")
        classes_seen = set()
        for tr in all_trs:
            cls = tr.get("class")
            if cls:
                classes_seen.add(" ".join(cls))
        print(f"  all <tr> classes seen in this container: {classes_seen}")
        print()


if __name__ == "__main__":
    main()
