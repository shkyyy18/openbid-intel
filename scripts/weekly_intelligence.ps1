param(
  [int]$MaxPages = 10,
  [int]$HistoryDays = 180,
  [int]$MaxDetails = 100,
  [switch]$NoPush
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $root 'src'
Set-Location $root
$args = @('run.py', 'intelligence', '--max-pages', $MaxPages, '--history-days', $HistoryDays, '--max-details', $MaxDetails)
if ($NoPush) { $args += '--no-push' }
python @args
exit $LASTEXITCODE
