# Data Sources and Compliance

## Default sources

The default configuration uses public list pages on the China Government Procurement Network for local and central open tenders and award notices. Procurement-intention entries remain disabled until a dedicated connector is implemented and verified.

## Configuration

Top-level fields in `config/sources.json`:

- `request_interval_seconds`: delay between requests; default is one second;
- `max_detail_fetches`: total detail-page budget for one run;
- `max_pages`: default page limit per source;
- `history_days`: default look-back window;
- `priority_detail_terms`: priority account, region, and product terms;
- `sources`: source definitions.

A source definition requires an ID, display name, connector type, public URL, notice stage, and enabled flag. A source can override `max_pages` and `history_days`.

## Collection semantics

- `--max-pages` limits pagination for each source.
- `--history-days` stops historical traversal outside the requested window.
- `--max-details` is a global budget shared by all enabled sources.
- Award sources use their detail allocation to extract suppliers and amounts.
- A detail-page failure is recorded as a warning and does not discard list records.
- The official source URL is retained. Sales decisions must be based on the official notice and attachments.

## Compliance boundary

This project accesses only public pages that do not require authentication and uses low-frequency requests. Contributors must not:

- bypass login, CAPTCHA, paywalls, IP restrictions, or other access controls;
- disable TLS certificate validation;
- use high-concurrency scraping that places unreasonable load on a service;
- collect or publish non-public procurement files or sensitive personal data;
- present a generated summary as a substitute for formal tender documents.

If rules, page structure, or public accessibility change, disable the source first. Prefer an official API, open-data service, RSS feed, email subscription, export, or manual import.

## Adding a connector

The connector registry currently includes `ccgp_list` and `rss_atom`. `rss_atom` supports RSS 2.0 and Atom feeds using only the Python standard library. See `samples/sources.rss.example.json` for a sanitized configuration.

A connector implements the `SourceConnector` protocol in `src/bid_intel/connectors.py`: it declares a unique `type_name` and returns `ConnectorOutput` from `collect(source, context)`. The shared `ConnectorContext` supplies the fetch function, request interval, history cutoff, page and detail budgets, and priority terms. Register new adapters through a `ConnectorRegistry`; do not add another source-type conditional to the collection loop.

A structurally different website should receive a dedicated connector and offline HTML, XML, or JSON fixtures rather than being forced through an existing parser.

Tests for a new connector should cover list fields, detail fields, encoding, relative URLs, missing values, structural changes, pagination, history cutoffs, global detail budgets, and failure isolation. CI must not access real websites. Perform live verification manually at a low request rate and record the date, source, and failures.
