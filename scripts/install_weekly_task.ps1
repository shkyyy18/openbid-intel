param(
  [string]$TaskName = 'OpenBidIntelWeekly',
  [ValidateSet('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')]
  [string]$DayOfWeek = 'Sunday',
  [string]$At = '09:00'
)
$ErrorActionPreference = 'Stop'
$script = (Resolve-Path (Join-Path $PSScriptRoot 'weekly_intelligence.ps1')).Path
$time = [DateTime]::ParseExact($At, 'HH:mm', [Globalization.CultureInfo]::InvariantCulture)
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$script`""
$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek $DayOfWeek -At $time
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2)
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description 'Weekly OpenBid Intel tender history and competitive intelligence report' -Force | Out-Null
Write-Host "Scheduled task $TaskName created; runs every $DayOfWeek at $At."
