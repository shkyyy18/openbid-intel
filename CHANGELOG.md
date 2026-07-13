# Changelog

All notable changes to OpenBid Intel are documented here.

## [Unreleased]

### Added

- `openbid explain` with text and JSON score-contribution output for testing a notice without writing to SQLite.
- Structured score contributions for business-line evidence, buyer terms, stage, region, priority accounts, budget, recency, deadlines, and score caps.
- A vendor-, buyer-, and region-neutral `logistics` profile pack for transport, warehousing, fulfillment, cold-chain, fleet technology, and logistics equipment.
- A neutral `facilities-management` profile pack for property operations, environmental services, and building technical maintenance.
- Repeatable `--profile-overlay` composition for layering ignored private sales rules onto public industry packs.
- A synthetic partial-overlay example with deterministic merge, validation, and privacy guidance.

### Changed

- Added deterministic publication-recency scoring and clearer missing-budget or missing-deadline risks.
- Improved near-deadline recommended actions to focus on response feasibility.

## [0.4.0] - 2026-07-12

### Added

- A typed connector protocol and registry for community source adapters.
- A zero-dependency RSS 2.0 and Atom connector with relative URL handling, date normalization, history cutoffs, deduplication, and offline XML fixtures.
- A sanitized RSS source configuration example and connector-authoring documentation.
- A reproducible GitHub Pages workflow that publishes only the synthetic dashboard demo.
- Public-output privacy checks for both literal and escaped private company terms.
- JSON Schema 2020-12 documents for profiles and source configuration, published with the live site and included in wheels.
- `openbid validate-config` with zero-dependency path-aware validation and duplicate-ID checks.
- `openbid export` for Excel-friendly CRM CSV files with an explicit safe field allowlist.
- A general education procurement profile covering digital learning, teaching/lab equipment, and campus services.
- `openbid init` for validated first-run profile/source setup with safe overwrite behavior and automation flags.
- Public profile-pack authoring and privacy review guidelines.

### Changed

- Replaced company-specific scoring actions and supplier-report wording with industry-neutral language.

## [0.3.0] - 2026-07-12

### Added

- A self-contained, responsive HTML opportunity dashboard generated directly from SQLite.
- Browser-side search and filters for stage, region, and business line without a web server.
- Pipeline metrics, explainable score reasons, recommended actions, and safe official-notice links.
- `openbid dashboard` with score, limit, output, and title options.
- Automatic HTML dashboard generation in the cross-industry demo.
- A real dashboard preview image in the README.
- HTML escaping and unsafe URL protection tests.

## [0.2.0] - 2026-07-12

### Added

- Five built-in profile packs for IT and digital, medical and laboratory, construction, marketing services, and energy and sustainability.
- `openbid profiles` and `openbid init-profile` commands for discovering and creating editable industry configurations.
- Flexible English and Chinese field aliases for JSON, JSONL, and CSV imports.
- Custom import mappings with `openbid import --mapping`.
- Amount normalization for common million, billion, ten-thousand-yuan, and hundred-million-yuan formats.
- Cross-industry synthetic demo data and profile/importer tests.

### Changed

- Repositioned the public project as a general-purpose tender intelligence toolkit instead of a niche sales configuration.
- Replaced the public default profile with the broadly useful `it-digital` pack.
- Made detail-fetch prioritization industry- and region-neutral unless terms are explicitly configured.
- Expanded release checks to require the profile-pack implementation and a bundled pack.

## [0.1.0] - 2026-07-12

### Added

- Local SQLite notice store with deduplication and collection history.
- JSON, JSONL, and CSV imports.
- Configurable, explainable opportunity scoring.
- Conservative CCGP public-list connector with pacing and fetch budgets.
- Markdown opportunity digests and optional Feishu notifications.
- Human sales feedback workflow.
- Historical award supplier and buyer-relationship analysis.
- Daily and weekly Windows Task Scheduler helpers.
- Offline release checks and cross-platform CI.
