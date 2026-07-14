# End-to-end synthetic opportunity triage

This case study shows the product loop with bundled synthetic data. It is reproducible offline and does not represent live procurement opportunities.

## The question

Can a sales or bid team take a mixed tender export and quickly separate likely IT opportunities from unrelated notices without sending data to a hosted service?

## Run it

```bash
git clone https://github.com/shkyyy18/openbid-intel.git
cd openbid-intel
python run.py demo
```

The command imports six synthetic notices, removes duplicates, scores every notice against the bundled `it-digital` profile, writes an explainable Markdown digest, and creates a self-contained HTML dashboard.

## Reproducible result

With the current bundled sample and profile:

| Notice | Score | Triage result |
|---|---:|---|
| City data platform and AI knowledge assistant RFP | 100 | Priority opportunity |
| University cybersecurity operations center procurement | 100 | Priority opportunity |
| Public building renovation and HVAC upgrade | 18 | Low relevance |
| Hospital diagnostic imaging equipment purchase | 17 | Low relevance |
| Solar and battery storage microgrid project | 14 | Low relevance |
| Office cafeteria operation service | 12 | Low relevance |

The useful result is not a generic summary. It is a ranked queue with matched capabilities, risk notes, deadlines, buyer context, and recommended next actions. A reviewer can open the two high-priority notices first and leave the unrelated notices for later review.

## What remains under human control

OpenBid Intel does not decide whether to bid. The user must still verify:

- the official notice and attachments;
- deadlines, amounts, qualifications, and procurement stage;
- whether the organization can actually deliver the requested scope;
- legal, commercial, and source-access constraints;
- final CRM stage and sales ownership.

The scoring profile is editable and every score is explainable. Feedback can be recorded and evaluated through calibration reports rather than silently changing weights.

## Adapt the loop to one industry

```bash
python run.py profiles
python run.py init education --source-template rss
python run.py --profile config/profile.local.json --sources config/sources.local.json demo
```

For a real evaluation, replace the sample with a sanitized CSV, JSON, JSONL, RSS, or Atom export you are permitted to use. Keep customer-specific keywords and private notes in ignored local configuration.

## Ten-minute validation checklist

- [ ] The synthetic demo completes without credentials or network access.
- [ ] The dashboard opens as one local HTML file.
- [ ] The top-ranked items make sense for the selected profile.
- [ ] Every score exposes reasons and risks.
- [ ] An unrelated notice receives a visibly lower score.
- [ ] A sanitized export from the intended workflow can be mapped without changing private defaults.

If the ranking does not match your workflow, open a Discussion with your industry, current input format, three positive keywords, three exclusion terms, and the action you take after an opportunity is qualified. Do not post private customer data or live credentials.
