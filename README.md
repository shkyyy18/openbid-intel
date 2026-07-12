<div align="center">

<img src="docs/assets/openbid-hero.svg" alt="OpenBid Intel pipeline" width="100%">

# OpenBid Intel

**Turn public tender notices into ranked sales opportunities - locally.**

[![Tests](https://github.com/shkyyy18/openbid-intel/actions/workflows/tests.yml/badge.svg)](https://github.com/shkyyy18/openbid-intel/actions/workflows/tests.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB)](https://www.python.org/)
[![MIT License](https://img.shields.io/badge/license-MIT-22c55e)](LICENSE)
[![Zero runtime dependencies](https://img.shields.io/badge/runtime_dependencies-0-8b5cf6)](pyproject.toml)

[Quick start](#30-second-quick-start) | [How it works](#how-it-works) | [Customize](#bring-your-own-sales-profile) | [Roadmap](ROADMAP.md)

</div>

Procurement portals are fragmented. Plain keyword alerts create noise. Generic summaries do not know your product lines, target accounts, regions, or deal threshold. **OpenBid Intel** is a local-first pipeline that collects or imports notices, normalizes and deduplicates them, scores each opportunity against your own sales profile, produces an actionable digest, and preserves human feedback.

> OpenBid Intel is an intelligence and triage tool, not a bidding database or legal source of truth. Always verify deadlines, amounts, qualifications, and attachments on the official notice page.

## Why OpenBid Intel

- **Bring your own context:** products, strong and related terms, target accounts, regions, budget floor, negative terms, and stage weights are plain JSON.
- **Local-first by design:** notices, scores, feedback, and reports stay in your SQLite database unless you explicitly send a digest.
- **Useful before you add a crawler:** import JSON, JSONL, or CSV from exports and existing workflows.
- **Built-in China connector:** includes a conservative connector for public list pages on the China Government Procurement Network (CCGP).
- **Competitor discovery:** mines historical award notices to surface recurring suppliers and buyer-supplier relationships.
- **Zero runtime dependencies:** the CLI uses only the Python standard library.

## 30-second quick start

Requires Python 3.11 or newer.

```bash
git clone https://github.com/shkyyy18/openbid-intel.git
cd openbid-intel
python run.py demo
```

The demo imports synthetic RF and CAE procurement notices, scores them, and writes `reports/demo_digest.md`.

Install the CLI locally:

```bash
python -m pip install -e .
openbid demo
openbid stats
```

Windows users can also run `bid-intel.cmd demo` without changing PowerShell execution policy.

## What you get

| Capability | Command | Output |
|---|---|---|
| Import JSON, JSONL, or CSV | `openbid import notices.json --score` | Normalized, deduplicated records |
| Collect configured public pages | `openbid collect --score` | New notices and collection run log |
| Score against your profile | `openbid score --all` | 0-100 score, reasons, risks, actions |
| Generate opportunity digest | `openbid digest --min-score 50` | Markdown or terminal report |
| Daily pipeline | `openbid daily --no-push` | Collection, scoring, dated digest |
| Record sales feedback | `openbid feedback 42 VERDICT --note "owner assigned"` | Auditable human decision |
| Analyze award suppliers | `openbid competitors` | Supplier ranking and history |
| Build intelligence bundle | `openbid intelligence --no-push` | Digest, account, competitor, quality reports |
| Verify a release or install | `openbid release-check` | Fully offline checks |

The feedback verdicts currently use Chinese labels. Run `openbid feedback --help` to see the accepted values.

## How it works

```text
public pages / JSON / JSONL / CSV
                |
                v
 COLLECT -> NORMALIZE -> DEDUPE -> SCORE -> DIGEST -> FEEDBACK
                |                    |            |
                +------ SQLite ------+------------+
                                      |
                                      +-> supplier and buyer relationships
```

Scoring is deterministic and explainable. It combines:

- strong and related product terms;
- procurement-stage weighting;
- buyer-category terms;
- target-account aliases and weights;
- region fit;
- minimum deal threshold;
- negative and noise terms;
- recency and deadline signals.

Each selected notice includes reasons, risks, recommended next actions, and the original URL. Tune the profile without changing Python code.

## Bring your own sales profile

Start with `config/profile.example.json` and save your private copy as `config/profile.local.json`:

```bash
cp config/profile.example.json config/profile.local.json
openbid --profile config/profile.local.json demo
```

A minimal product line looks like this:

```json
{
  "company": "ExampleCo",
  "min_budget_cny": 500000,
  "business_lines": [
    {
      "id": "rf_test",
      "name": "RF test systems",
      "base_score": 25,
      "strong_terms": ["antenna measurement system", "near-field measurement"],
      "related_terms": ["anechoic chamber", "positioner"]
    }
  ]
}
```

`config/*.local.json`, `.env`, SQLite databases, and generated reports are ignored by Git. Keep customer notes, internal pricing, bid strategy, credentials, restricted documents, and non-public requirements outside the repository.

## Inputs and connectors

JSON and JSONL records may include `title`, `url`, `source`, `published_at`, `deadline_at`, `stage`, `buyer`, `region`, `budget_cny`, `content`, `award_supplier`, and `award_amount_cny`. CSV uses the same headers.

`config/sources.json` enables selected CCGP public list pages. The collector is intentionally conservative: request pacing, page limits, history windows, detail-fetch budgets, and failure isolation are configurable. CI never accesses live websites.

OpenBid Intel does **not** claim complete national coverage. Public portals change, block automation, or expose incomplete metadata. Add connectors only when ordinary public access and site terms permit it; never bypass authentication, CAPTCHA, or access controls.

## Competitor intelligence

Award notices can reveal recurring supplier-buyer relationships. OpenBid Intel extracts award suppliers, ranks frequency and value, filters results through the same product profile, and builds priority-account reports.

These are **leads for verification**, not verified competitor classifications. A supplier may be an OEM, reseller, integrator, service provider, or unrelated vendor with a similar name.

## Feishu notifications

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

See the [Operations Guide](docs/OPERATIONS.md), [Data Sources](docs/DATA_SOURCES.md), and [Public Data Handling](docs/DATA_HANDLING.md).

## Project status

OpenBid Intel is an early, usable release. The scoring and local workflow are ready for real validation; source coverage is deliberately small. Contributions with sanitized fixtures, compliant connectors, scoring improvements, and international portal adapters are welcome.

See [ROADMAP.md](ROADMAP.md) and [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT (c) 2026 shkyyy18
