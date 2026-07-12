param([string]$TaskName = 'OpenBidIntel')
$ErrorActionPreference = 'Stop'
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Write-Host "Scheduled task $TaskName removed."
