param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$Args
)
$env:PYTHONPATH = Join-Path $PSScriptRoot 'src'
python (Join-Path $PSScriptRoot 'run.py') @Args
exit $LASTEXITCODE
