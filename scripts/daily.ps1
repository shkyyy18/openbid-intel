param(
  [int]$MinScore = 50,
  [int]$Limit = 15,
  [int]$MaxPages = 3,
  [int]$HistoryDays = 14,
  [int]$MaxDetails = 40,
  [switch]$NoPush
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $root 'src'
Set-Location $root
$args = @('run.py', 'daily', '--min-score', $MinScore, '--limit', $Limit, '--max-pages', $MaxPages, '--history-days', $HistoryDays, '--max-details', $MaxDetails)
if ($NoPush) { $args += '--no-push' }
python @args
exit $LASTEXITCODE
