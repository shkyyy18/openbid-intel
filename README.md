<div align="center">

<img src="docs/assets/openbid-hero.svg" alt="OpenBid Intel pipeline" width="100%">

# OpenBid Intel

**Turn messy tender feeds into ranked opportunities for any industry - locally.**

[![Tests](https://github.com/shkyyy18/openbid-intel/actions/workflows/tests.yml/badge.svg)](https://github.com/shkyyy18/openbid-intel/actions/workflows/tests.yml)
[![Release](https://img.shields.io/github/v/release/shkyyy18/openbid-intel)](https://github.com/shkyyy18/openbid-intel/releases/latest)
[![Contributors](https://img.shields.io/github/contributors/shkyyy18/openbid-intel)](https://github.com/shkyyy18/openbid-intel/graphs/contributors)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB)](https://www.python.org/)
[![MIT License](https://img.shields.io/badge/license-MIT-22c55e)](LICENSE)
[![Zero runtime dependencies](https://img.shields.io/badge/runtime_dependencies-0-8b5cf6)](pyproject.toml)

[**Live demo**](https://shkyyy18.github.io/openbid-intel/) | [Quick start](#30-second-quick-start) | [Dashboard](#portable-html-dashboard) | [Industry packs](#built-in-industry-packs) | [Good first issues](https://github.com/shkyyy18/openbid-intel/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) | [Roadmap](ROADMAP.md)

</div>

Public procurement data is fragmented across portals, spreadsheets, subscriptions, email alerts, and internal exports. Keyword alerts are noisy, while generic summaries do not understand what your team sells.

**OpenBid Intel** is an open-source, local-first toolkit that normalizes tender notices, removes duplicates, ranks opportunities against an editable industry profile, creates an actionable digest, and learns from sales feedback. Start with CSV/JSON exports, choose an industry pack, and add compliant connectors only when you need them.

> OpenBid Intel is a triage and intelligence tool, not a bidding database or legal source of truth. Verify deadlines, amounts, qualifications, and attachments on the official notice page.

**Try it before installing:** the [live dashboard](https://shkyyy18.github.io/openbid-intel/) is rebuilt from synthetic data on every push to `main`; it contains no private or collected procurement data.

![OpenBid Intel opportunity dashboard](docs/assets/dashboard-preview.png)

## Why this project exists

- **Useful across industries:** the engine is not tied to one company, region, portal, or product category.
- **Fast first result:** nine built-in profile packs cover common procurement markets.
- **Bring almost any export:** JSON, JSONL, and CSV imports support common English and Chinese field aliases plus custom mappings.
- **Explainable ranking:** every score includes matched reasons, risks, and recommended next actions.
- **Portable visual dashboard:** generate one self-contained HTML file with search and filters; no server required.
- **Local-first:** notices, profiles, scores, feedback, and reports remain in SQLite unless you explicitly send a digest.
- **Connector-friendly, not scraper-first:** use exports immediately; add low-frequency public-source adapters with offline fixtures.
- **Zero runtime dependencies:** the CLI uses only the Python standard library.

## 30-second quick start

Requires Python 3.11 or newer.

```bash
git clone https://github.com/shkyyy18/openbid-intel.git
cd openbid-intel
python -m pip install -e .
openbid demo
```

The cross-industry demo imports six synthetic notices and ranks the IT, data, AI, and cybersecurity opportunities using the default `it-digital` profile. It writes both `reports/demo_digest.md` and the interactive `reports/demo_dashboard.html`. To run without installing, use `PYTHONPATH=src python run.py demo` (`$env:PYTHONPATH="src"` in PowerShell).

Create a private local configuration and try it with another industry pack:

```bash
openbid init education --source-template rss
openbid --profile config/profile.local.json --sources config/sources.local.json demo
```

## Verified demo output

The following outputs were captured from real runs of the commands above (Python 3.14, Windows; captured 2026-07-20). Scores that depend on the run date may drift slightly over time.

`openbid demo`:

```text
Demo complete: 6 new, 0 updated, 6 scored; digest reports\demo_digest.md; dashboard reports\demo_dashboard.html
```

Section headings of the generated `reports/demo_digest.md` - two IT opportunities rank at the cap while four unrelated notices are filtered to low relevance:

```text
## 1. [重点 100/100] City data platform and AI knowledge assistant RFP
## 2. [重点 100/100] University cybersecurity operations center procurement
## 3. [低相关 15/100] Public building renovation and HVAC upgrade
## 4. [低相关 14/100] Hospital diagnostic imaging equipment purchase
## 5. [低相关 11/100] Solar and battery storage microgrid project
## 6. [低相关 9/100] Office cafeteria operation service
```

`openbid explain --title "City data platform and AI knowledge assistant RFP" --buyer "Example City Digital Services Department" --stage "request for proposal" --region "Example Region" --budget-cny 4200000 --published-at 2026-07-12 --deadline-at 2026-08-15 --as-of 2026-07-13` (fully deterministic thanks to `--as-of`):

```text
Score: 57 (关注)
Business lines: Data, AI and cloud

Score contributions:
  +40  business_line: Data, AI and cloud - strong: data platform
  +3  buyer: Buyer-category terms - department
  +5  stage: request for proposal
  +2  procurement: Procurement language - request for proposal, rfp
  +0  region: Focus-region match - No configured focus region matched
  +2  budget: Known budget - CNY 4,200,000
  +5  recency: Publication recency - Published 1.0 days ago
  +0  deadline: Deadline window - 33.0 days remaining
```

The test suite (`python -m pytest tests -q`) reports `104 passed`.

Windows users can also run `bid-intel.cmd demo` without changing the PowerShell execution policy.

## See the complete triage loop

The [end-to-end synthetic case study](docs/END_TO_END_CASE_STUDY.md) shows a reproducible six-notice evaluation: two IT opportunities score 100, while four unrelated notices score between 12 and 18. It explains what the system automates, what remains a human decision, and how to adapt the workflow to one industry without publishing private data.

Use the [ten-minute validation checklist](docs/END_TO_END_CASE_STUDY.md#ten-minute-validation-checklist) before adding a live source. If you are evaluating OpenBid Intel for a real workflow, the [five-question user validation guide](docs/USER_VALIDATION.md) captures the minimum information needed for a useful next step.

## Portable HTML dashboard

Generate a polished, self-contained dashboard directly from the local SQLite database:

```bash
openbid dashboard --min-score 50 --output reports/dashboard.html
```

The file works offline and can be opened in any modern browser. It includes full-text search, stage/region/business-line filters, pipeline summary metrics, explainable score reasons, recommended actions, and safe links to official notices. No web server, JavaScript framework, or external asset is required.

## Built-in industry packs

| Profile pack | Typical opportunities |
|---|---|
| `it-digital` | Software, cloud, AI, data platforms, cybersecurity |
| `medical-lab` | Medical devices, diagnostics, lab and scientific instruments |
| `construction` | Buildings, renovation, civil works, HVAC and MEP |
| `marketing-services` | Branding, events, research, consulting and training |
| `energy-sustainability` | Solar, storage, efficiency, carbon and environmental services |
| `education` | Digital learning, teaching/lab equipment, campus services and infrastructure |
| `logistics` | Transportation, warehousing, fulfillment, cold-chain, fleet technology and equipment |
| `facilities-management` | Property/facility operations, cleaning, landscaping and building maintenance |
| `professional-services` | Management advisory, audit, tax, risk, legal and corporate services |

Create both ignored local configuration files in one step, or list and initialize only a profile pack:

```bash
openbid init education --source-template rss
openbid profiles
openbid init-profile energy-sustainability --output config/profile.local.json
```

`openbid init` validates both generated files, refuses to overwrite them unless `--force` is supplied, and prints the exact import and dashboard commands to run next. In a terminal it offers profile selection; in scripts and redirected sessions it safely defaults to `it-digital`. The optional RSS template is disabled until you replace its placeholder URL and explicitly enable it.

A profile pack is ordinary JSON, not a locked model. Fork it for a niche market, change product terms, add account aliases, set budget thresholds, or contribute a sanitized pack for a broadly useful sector. See [Profile pack authoring](docs/PROFILE_PACKS.md) for the public-pack contract and review checklist.

### Keep private rules in a local overlay

Use a built-in public pack directly and layer private accounts, territories, budget rules, or product phrases from an ignored partial JSON file:

```bash
cp samples/profile.overlay.example.json config/profile.local.json
openbid \
  --profile src/bid_intel/profiles/education.json \
  --profile-overlay config/profile.local.json \
  explain --title "Synthetic learning appliance procurement"
```

Repeat `--profile-overlay` to apply team and territory overlays from left to right. Dictionaries merge recursively; business lines merge by `id`; priority accounts merge by `name`; scalar lists are appended and de-duplicated. An explicit empty list clears the inherited list. The composed result is validated before scoring, while overlay configuration metadata and paths are not added to reports or score explanations; matched terms can still appear as normal scoring evidence. Keep overlays under `config/*.local.json`, which is ignored by Git.

## Validate configuration

Profile and source files are documented with JSON Schema 2020-12 under `schemas/`. The public files include relative `$schema` hints, while `openbid init-profile` writes a stable hosted schema URL so editors such as VS Code can provide completion and inline errors. Validate both active files without installing a third-party package:

```bash
openbid validate-config
openbid --profile config/profile.local.json validate-config --only profile
```

Validation reports exact JSON paths, missing required fields, invalid types and ranges, empty required arrays or strings, and duplicate business-line or source IDs before collection or scoring begins.

## Explain a score before importing

Test profile terms and scoring behavior without creating or writing a SQLite database:

```bash
openbid --profile config/profile.local.json explain \
  --title "Campus smart classroom upgrade" \
  --buyer "Example University" \
  --content "Learning platform, lecture capture, and interactive displays" \
  --stage "tender notice" \
  --region "Example Region" \
  --budget-cny 2000000 \
  --published-at 2026-07-12 \
  --deadline-at 2026-07-20 \
  --as-of 2026-07-13
```

The output shows each positive, negative, and zero-point contribution, including business-line evidence, buyer terms, stage, region, budget, publication recency, and deadline timing. The contribution points reconcile exactly to the final capped 0-100 score. Add `--json` for a stable machine-readable form suitable for tests, editors, or profile-authoring tools. `--as-of` makes time-based results reproducible.

## Import from any export

OpenBid Intel accepts a top-level JSON array, JSON objects containing `notices`, `items`, or `results`, JSONL, and CSV. It recognizes common source headers automatically.

```bash
openbid import procurement-export.csv --score
```

For unusual column names, provide a mapping from canonical OpenBid fields to source fields:

```bash
openbid import procurement-export.csv \
  --mapping samples/field_mapping.example.json \
  --score
```

Example mapping:

```json
{
  "title": "Project Name",
  "url": "Notice Link",
  "published_at": "Published Date",
  "budget_cny": "Estimated Value"
}
```

Amount parsing handles values such as `$1.25 million`, `1.2 billion`, `CNY 1.25 million`, and `CNY 200 million`. Canonical fields include `title`, `url`, `source`, `published_at`, `deadline_at`, `stage`, `buyer`, `region`, `budget_cny`, `content`, `award_supplier`, and `award_amount_cny`.

## What you get

| Capability | Command | Output |
|---|---|---|
| Discover profile packs | `openbid profiles` | Available industries and descriptions |
| Create an editable profile | `openbid init-profile it-digital` | Private local JSON configuration |
| Import exports | `openbid import notices.csv --score` | Normalized and deduplicated records |
| Collect configured public pages | `openbid collect --score` | New notices and collection run log |
| Test a sample against a profile | `openbid explain --title "Example RFP"` | Score contribution breakdown without database writes |
| Score against your profile | `openbid score --all` | 0-100 scores, reasons, risks, actions |
| Generate an opportunity digest | `openbid digest --min-score 50` | Markdown or terminal report |
| Generate an HTML dashboard | `openbid dashboard --min-score 50` | Interactive, self-contained HTML |
| Export qualified opportunities | `openbid export --min-score 50` | CRM-friendly Excel CSV |
| Run a daily pipeline | `openbid daily --no-push` | Collection, scoring, dated digest |
| Record sales feedback | `openbid feedback 42 VERDICT --note "owner assigned"` | Auditable human decision |
| Calibrate score thresholds | `openbid calibrate --threshold 50` | Feedback-based precision, recall, F1, and error review |
| Route across profiles | `openbid route --min-score 40` | Best-fit industry or product-team assignment with alternatives |
| Analyze award suppliers | `openbid competitors` | Supplier ranking and buyer history |
| Build an intelligence bundle | `openbid intelligence --no-push` | Digest, account, supplier and quality reports |
| Verify an install or release | `openbid release-check` | Fully offline checks |

The CSV export uses UTF-8 with a BOM (`utf-8-sig`) so current Excel versions detect non-ASCII text without an import wizard. It contains only stable notice IDs, opportunity fields, score, matched business lines, URL, and latest verdict. Notice content, raw payloads, webhook secrets, and internal feedback notes are excluded by default.

Feedback verdicts currently use Chinese labels. Run `openbid feedback --help` to see the accepted values. Calibration uses only the latest verdict for each scored notice: relevant workflow outcomes such as `相关`, `已跟进`, `已投标`, `中标`, and `失标` are positive labels; `不相关` is negative; and `放弃` is ignored because it may reflect eligibility or commercial constraints rather than relevance. Internal feedback notes are never included in calibration reports.

Generate a human-readable or machine-readable calibration report:

```bash
openbid calibrate --threshold 50
openbid calibrate --threshold 50 --json
openbid calibrate --threshold 50 --output reports/calibration.md
```

The recommended threshold is a deterministic, descriptive best-F1 result from the labels currently available. It never changes a profile automatically, and small or single-class samples should be treated as preliminary.

## Multi-profile opportunity routing

A shared procurement feed often serves several industries, product portfolios, or sales teams. Route every stored notice against all bundled profiles without overwriting the active single-profile scores:

```bash
openbid route --min-score 40
openbid route --min-score 40 --json
openbid route --profile-id education --profile-id it-digital
openbid route --profile-path config/custom-profile.json --output reports/routing.md
```

With no profile selector, `route` evaluates every bundled industry pack. The highest score becomes the deterministic assignment, ties are resolved by profile ID, and `--top-profiles` retains bounded alternatives for cross-sell or review. Custom profile files are schema-validated, duplicate profile IDs are rejected, and routing remains read-only: it does not replace scores used by the normal digest or dashboard.

Routing reports expose only selected notice fields and score explanations. Raw imported payloads, notice content, feedback notes, profile file paths, and database internals are not included.

## How it works

```text
CSV / JSON / JSONL / public connectors
                  |
                  v
       NORMALIZE -> DEDUPE -> SCORE -> DIGEST -> FEEDBACK
                         |       |         |
                         +---- SQLite -----+
                                  |
                                  +-> supplier and buyer relationships
```

Scoring is deterministic and configurable. It combines:

- strong and related product terms;
- procurement-stage weighting;
- buyer-category terms;
- target-account aliases and weights;
- region fit;
- minimum deal threshold;
- negative and noise terms;
- recency and deadline signals.

No source, region, or niche industry receives a hidden hard-coded advantage. Collection detail priority follows the active source configuration; opportunity ranking follows the active profile.

## Customize without exposing private sales data

The public repository contains generic examples. Keep your real sales configuration in ignored local files:

```bash
openbid init it-digital
openbid --profile config/profile.local.json --sources config/sources.local.json import notices.csv --score
openbid --profile config/profile.local.json digest --min-score 50
```

`config/*.local.json`, `.env`, SQLite databases, and generated reports are ignored by Git. Do not commit customer lists, internal pricing, restricted requirements, credentials, or bid strategy.

This separation is intentional:

```text
Open-source core                 Private local deployment
-----------------------------    --------------------------------
normalization and deduplication  customer and account aliases
explainable scoring engine       niche product vocabulary
industry profile packs           territory and budget thresholds
connector interface              internal notes and sales feedback
sanitized fixtures               private sources and credentials
```

## Inputs and connectors

Two connector types are included:

- `ccgp_list`: a conservative adapter for selected public list pages on the China Government Procurement Network;
- `rss_atom`: a generic standard-library RSS 2.0 and Atom feed connector with relative-link handling, history cutoffs, deduplication, and optional item limits.

Copy `samples/sources.rss.example.json` to an ignored local source configuration and replace the synthetic URL with a public feed you are permitted to access. The connector registry in `src/bid_intel/connectors.py` is the stable extension point for community adapters. Each connector receives a shared context for pacing, history limits, detail budgets, and fetching, and returns normalized `Notice` records plus non-fatal warnings.

These adapters are examples, not the product boundary, and OpenBid Intel does **not** claim complete national or global coverage. Public portals change, block automation, and expose incomplete metadata. Add connectors only when ordinary public access and site terms permit it. Never bypass authentication, CAPTCHA, paywalls, or access controls. Prefer official APIs, open-data feeds, RSS, email exports, and manual exports where available.

See [Data Sources](docs/DATA_SOURCES.md) and [Public Data Handling](docs/DATA_HANDLING.md).

## Supplier and buyer intelligence

Award notices can reveal recurring supplier-buyer relationships. OpenBid Intel extracts award suppliers, ranks frequency and value, filters results through the active industry profile, and builds priority-account reports.

These are leads for verification, not verified competitor classifications. A supplier may be an OEM, reseller, integrator, service provider, or unrelated vendor with a similar name.

## Optional Feishu notifications

Copy `.env.example` to `.env`, then add a Feishu group-bot webhook and optional signing secret:

```text
FEISHU_WEBHOOK_URL=
FEISHU_WEBHOOK_SECRET=
```

Run `openbid doctor`, then remove `--no-push` from daily or intelligence commands. Secrets are never required for local reports.

## Scheduling on Windows

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install_task.ps1 -At 08:30
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install_weekly_task.ps1 -DayOfWeek Sunday -At 09:00
```

See the [Operations Guide](docs/OPERATIONS.md).

## Good first contributions

The easiest ways to extend OpenBid Intel are intentionally modular:

- contribute a sanitized industry profile pack;
- add a fixture-tested importer alias or amount format;
- build a compliant connector for a public procurement source;
- improve profile schema validation;
- improve the portable HTML dashboard or add a CRM-friendly export.

Browse the [open good-first-issue queue](https://github.com/shkyyy18/openbid-intel/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22), read [CONTRIBUTING.md](CONTRIBUTING.md), and open a Discussion for industry validation or source-compliance questions. Never submit private customer data or live credentials.

## Project status

OpenBid Intel is an early but usable release. Import, deduplication, scoring, reporting, the portable dashboard, feedback, supplier analysis, and the local workflow are ready for real-world validation. Source coverage remains deliberately small while the project prioritizes trustworthy, reusable foundations over a long list of brittle scrapers.

See [ROADMAP.md](ROADMAP.md).

## License

MIT (c) 2026 shkyyy18
