[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

$pidFile = Join-Path $repoRoot "logs\ai-publisher\ai-publisher.pid.json"

if (-not (Test-Path -LiteralPath $pidFile -PathType Leaf)) {
    Write-Host "No AI publisher PID file found. Nothing to stop."
    exit 0
}

$metadata = Get-Content -LiteralPath $pidFile -Raw | ConvertFrom-Json
if (-not $metadata.pid) {
    Write-Warning "PID file did not contain a pid. Removing stale file."
    Remove-Item -LiteralPath $pidFile -Force
    exit 0
}

$process = Get-CimInstance Win32_Process -Filter "ProcessId = $($metadata.pid)" -ErrorAction SilentlyContinue
if (-not $process) {
    Write-Host "Publisher wrapper PID $($metadata.pid) is not running. Removing stale PID file."
    Remove-Item -LiteralPath $pidFile -Force
    exit 0
}

$commandLine = [string]$process.CommandLine
if ($commandLine -notlike "*src.main*" -or $commandLine -notlike "*config/config.yaml*") {
    Write-Warning "PID $($metadata.pid) does not look like the AI publisher wrapper. Refusing to stop it automatically."
    Write-Host "Command line: $commandLine"
    exit 1
}

Stop-Process -Id $metadata.pid -Force
Remove-Item -LiteralPath $pidFile -Force

Write-Host "Stopped AI publisher wrapper PID $($metadata.pid)."
if ($metadata.log_path) {
    Write-Host "Last log: $($metadata.log_path)"
}
