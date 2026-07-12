param(
  [string]$TaskName = 'OpenBidIntel',
  [string]$At = '08:30'
)
$ErrorActionPreference = 'Stop'
$script = (Resolve-Path (Join-Path $PSScriptRoot 'daily.ps1')).Path
$time = [DateTime]::ParseExact($At, 'HH:mm', $null)
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$script`""
$trigger = New-ScheduledTaskTrigger -Daily -At $time
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description 'Daily OpenBid Intel tender intelligence collection and digest' -Force | Out-Null
Write-Host "Scheduled task $TaskName created; runs daily at $At."
