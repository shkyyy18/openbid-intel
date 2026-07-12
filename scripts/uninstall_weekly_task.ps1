param([string]$TaskName = 'OpenBidIntelWeekly')
$ErrorActionPreference = 'Stop'
$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($null -eq $task) {
  Write-Host "Scheduled task $TaskName does not exist; nothing to remove."
  exit 0
}
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Write-Host "Scheduled task $TaskName removed."
