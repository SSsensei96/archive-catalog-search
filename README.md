# Archive catalogue search

Tools for collecting a three-level archival catalogue (fonds, inventories, and files), building a JSONL search index, and searching that index offline.

[Search the archive snapshot](https://sssensei96.github.io/archive-catalog-search/) · [View the portfolio](https://sssensei96.github.io/ilyas-butayev/)

## Try it

The browser search loads the complete supplied archive_full.json snapshot. It contains **775 fonds and 2,100 inventories, but no individual file records**. Search with all or any terms, or load your own compatible JSONL index. Uploaded files stay in your browser. The demo makes no requests to the live catalogue.

To search the supplied snapshot from the command line, first build a flat index:

    python build_index.py --input docs/archive_full.json

Then search it:

    python search_archive.py "целина" --index search_index.jsonl
    python search_archive.py --any "Алма-Атинский" "Карагандинский" --index search_index.jsonl

Without --input, the index builder reads newly collected files from an output_funds directory. The supplied snapshot is available in docs/archive_full.json; it is also served directly by the browser demo.

    python build_index.py

## Catalogue access

The supplied scraper source is included for review, but the original package noted restrictions on automated access to the catalogue. Check the current site rules and obtain permission before running the crawler. The browser demo does not run a live crawl. The snapshot contains public catalogue descriptions, not the underlying archival documents. The official catalogue is the authority for current records: https://archive.president.kz/ru/funds/ecatalog/

## Files

- scrape_archive.py: catalogue crawler with resume, pacing, and concurrent workers.
- build_index.py: turn collected fund files into a JSONL search index.
- search_archive.py: offline command-line search.
- debug_fetch.py: local diagnostic script for HTTP and parsing behavior.
- docs/: browser-local search and the complete supplied archive_full.json snapshot.

The JSON is a captured snapshot and may differ from the current official catalogue. Its filename does not imply that every file-level record was captured.
