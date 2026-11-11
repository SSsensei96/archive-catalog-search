# Archive catalogue search

Tools for collecting a three-level archival catalogue (fonds, inventories, and files), building a JSONL search index, and searching that index offline.

[Try the browser demo](https://sssensei96.github.io/archive-catalog-search/) · [View the portfolio](https://sssensei96.github.io/ilyas-butayev/)

## Try it

The browser demo opens eight **fictional sample records**. Search with all or any terms, or load your own compatible JSONL index. Uploaded files stay in your browser. The demo makes no requests to the catalogue.

The command-line search also works with the sample:

    python search_archive.py "целина" --index docs/sample_index.jsonl
    python search_archive.py --any "education" "industry" --index docs/sample_index.jsonl

The local index builder reads collected files from an output_funds directory:

    python build_index.py

## Catalogue access

The supplied scraper source is included for review, but the original package noted restrictions on automated access to the catalogue. Check the current site rules and obtain permission before running the crawler. This repository does not contain a real catalogue dump or run a live crawl.

## Files

- scrape_archive.py: catalogue crawler with resume, pacing, and concurrent workers.
- build_index.py: turn collected fund files into a JSONL search index.
- search_archive.py: offline command-line search.
- debug_fetch.py: local diagnostic script for HTTP and parsing behavior.
- docs/: browser-local demo and fictional sample data.

The sample records are invented for the demo and are not historical claims.
