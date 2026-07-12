# Profile pack authoring

A profile pack turns a generic procurement stream into explainable opportunity rankings for one broad market. Public packs must be reusable across organizations, regions, and vendors; keep customer aliases, territories, prices, credentials, and bid strategy in ignored `config/*.local.json` files.

## Start from an existing pack

```bash
openbid profiles
openbid init-profile education --output config/profile.local.json
openbid --profile config/profile.local.json validate-config --only profile
```

Built-in packs live under `src/bid_intel/profiles/`. Each file is ordinary JSON and is validated against `schemas/profile.schema.json`.

## Required business-line fields

Every entry in `business_lines` needs:

- `id`: stable lowercase identifier, preferably `snake_case`;
- `name`: short human-readable label;
- `strong_terms`: phrases that are highly specific to the product or service;
- `related_terms`: supporting terms that strengthen a match but should not dominate it.

`base_score` is optional. Keep scores comparable with existing packs; terms and visible scoring reasons should do most of the work.

## Recommended pack structure

A broadly useful pack should normally include:

1. `meta.id`, `meta.title`, and `meta.description`;
2. two to five distinct business lines;
3. English terms and, where useful, additional language variants;
4. procurement-stage weights that favor early opportunities over award or cancellation notices;
5. buyer-category terms and noise-reduction terms;
6. empty public defaults for regions, account lists, and budget thresholds.

Do not include real customer names, internal account aliases, a salesperson's territory, private product codenames, minimum deal rules, or proprietary competitive intelligence.

## Term design

Prefer phrases over isolated words. For example, `learning management system` is safer than `system`, and `laboratory equipment` is safer than `equipment`. Avoid duplicate terms across business lines unless the overlap is intentional and explainable.

Use `negative_terms` only for recurring false positives such as recruitment, admissions, property sales, or consumer finance. Do not use negative terms to suppress competitors or specific buyers.

## Local verification

Run the complete offline checks before opening a pull request:

```bash
python -m pytest -q
python -m compileall -q src tests run.py
python run.py validate-config
python run.py --db data/release_check.db release-check
git diff --check
```

Also initialize the pack as an end user would:

```bash
openbid init your-pack-id --profile-output config/profile.local.json --sources-output config/sources.local.json --non-interactive
```

The generated files must validate, remain ignored by Git, and contain no private data.

## Pull-request checklist

- The pack represents a broad market rather than one vendor or account.
- At least two business lines are meaningfully different.
- Terms are specific enough to avoid obvious noise.
- Public defaults contain no territory, budget, customer, or credential data.
- `openbid profiles` and `openbid init-profile <id>` work.
- Every built-in profile still passes schema validation.
- The README industry-pack table is updated.
- Fixtures and examples are synthetic or safely sanitized.

A profile pack is accepted for usefulness and maintainability, not for the number of keywords it contains.
