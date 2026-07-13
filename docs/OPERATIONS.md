# Operations Guide

Run all commands from the repository root. On Windows, prefer `bid-intel.cmd` because it does not depend on the local PowerShell script execution policy.

## First checks

```powershell
.\bid-intel.cmd release-check
.\bid-intel.cmd doctor
```

`release-check` is fully offline. It validates repository files, JSON configuration, baseline profile counts, SQLite access, ignore rules, and the Python version. `doctor` checks the local runtime and Feishu configuration.

## Daily opportunity scan

```powershell
.\bid-intel.cmd daily --max-pages 3 --history-days 14 --max-details 40 --no-push
```

Reports are written under `reports/`. Remove `--no-push` after a valid Feishu webhook has been configured in `.env`.

Review every selected opportunity against the official notice and attachments. In particular, verify the amount, deadline, buyer identity, technical scope, eligibility terms, and current notice stage. Record the sales decision with the `feedback` command.

## Feedback and score calibration

Record decisions consistently, then compare the current cutoff with the latest verdict for each scored notice:

```powershell
.\bid-intel.cmd feedback 42 相关
.\bid-intel.cmd feedback 57 不相关
.\bid-intel.cmd calibrate --threshold 50
.\bid-intel.cmd calibrate --threshold 50 --json --output reports/calibration.json
```

The report includes the confusion matrix, precision, recall, specificity, F1, accuracy, score-band positive rates, and false-positive/false-negative examples. It recommends a threshold by maximizing F1, then precision, recall, and the higher threshold. This recommendation is descriptive only and never edits a profile.

Only the latest feedback verdict per notice is used. Relevant workflow outcomes, including `失标`, count as positive relevance evidence; `不相关` is negative; and `放弃` is ignored as ambiguous. Feedback notes are never selected for the report. Treat results based on fewer than 20 comparable labels or a single label class as preliminary.

## Weekly history and competitive intelligence

```powershell
.\bid-intel.cmd intelligence --max-pages 10 --history-days 180 --max-details 100 --no-push
```

The default output directory is `reports/intelligence/`. The bundle includes an opportunity digest, an overall supplier report, one report per configured priority account, and a data-quality report.

Supplier roles are heuristic labels. They are not verified corporate facts and must be checked using official websites, company records, product evidence, and customer conversations.

## Windows scheduled tasks

Install the daily task:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install_task.ps1 -At 08:30
```

Remove it:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\uninstall_task.ps1
```

Install the weekly task (Sunday at 09:00 by default):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install_weekly_task.ps1 -DayOfWeek Sunday -At 09:00
```

Remove it:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\uninstall_weekly_task.ps1
```

The task stores the resolved absolute path of the script. Reinstall scheduled tasks after moving the repository.

## Backup and restore

Back up these items:

- `data/bids.db`: notices, scores, feedback, and collection history;
- `config/profile.json`: products, regions, account aliases, and thresholds;
- `config/sources.json`: public sources and collection limits;
- `.env`: local secrets; keep it outside public repositories and shared archives.

Stop an active collection before copying the SQLite file. Restore by placing the database back at the configured path.

## Troubleshooting

- **PowerShell blocks local scripts:** use `bid-intel.cmd` for normal commands and explicit `-ExecutionPolicy Bypass` only for the provided task-install commands.
- **One source fails:** inspect `bid-intel.cmd runs`. Other sources continue running.
- **The digest is empty:** inspect `stats` and `quality`, then review score thresholds, time windows, and the detail-page budget.
- **The competitor report is empty:** the database may contain no product-related award. Do not label every award supplier as a competitor merely to fill the report.
- **Feishu does not receive a message:** verify `.env`, webhook validity, and robot security settings. Local reports are still generated.
