# Changelog

All notable changes to OpenBid Intel are documented here.

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
