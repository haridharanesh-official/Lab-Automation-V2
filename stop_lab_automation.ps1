[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

$pidFile = Join-Path $repoRoot "logs\ai-publisher\ai-publisher.pid.json"
$mainPattern = "*-m src.main --config*config/config.yaml*"

function Get-AiPublisherProcesses {
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.CommandLine -and
            $_.CommandLine -like $mainPattern -and
            $_.CommandLine -like "*$repoRoot*"
        }
}

function Get-DescendantProcessIds([int]$ParentPid) {
    $children = @(Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq $ParentPid })
    $ids = @()
    foreach ($child in $children) {
        $ids += [int]$child.ProcessId
        $ids += Get-DescendantProcessIds -ParentPid ([int]$child.ProcessId)
    }
    return $ids
}

function Stop-KnownPublisherProcesses([int[]]$PreferredPids) {
    $pidSet = @{}
    foreach ($id in $PreferredPids) {
        if ($id -gt 0) {
            $pidSet[$id] = $true
        }
    }
    foreach ($process in Get-AiPublisherProcesses) {
        $pidSet[[int]$process.ProcessId] = $true
    }
    foreach ($id in @($pidSet.Keys | Sort-Object -Descending)) {
        $process = Get-Process -Id $id -ErrorAction SilentlyContinue
        if ($process) {
            Stop-Process -Id $id -Force -ErrorAction SilentlyContinue
            Write-Host "Stopped AI publisher process PID $id."
        }
    }
}

if (-not (Test-Path -LiteralPath $pidFile -PathType Leaf)) {
    $orphans = @(Get-AiPublisherProcesses)
    if ($orphans.Count -eq 0) {
        Write-Host "No AI publisher PID file found. Nothing to stop."
        exit 0
    }
    Write-Warning "No PID file found, but matching AI publisher process(es) are still running. Stopping matching repo publisher processes."
    Stop-KnownPublisherProcesses -PreferredPids @()
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
    Write-Host "Publisher wrapper PID $($metadata.pid) is not running. Checking for orphaned AI publisher children."
    Stop-KnownPublisherProcesses -PreferredPids @()
    Remove-Item -LiteralPath $pidFile -Force
    exit 0
}

$commandLine = [string]$process.CommandLine
if ($commandLine -notlike "*src.main*" -or $commandLine -notlike "*config/config.yaml*") {
    Write-Warning "PID $($metadata.pid) does not look like the AI publisher wrapper. Refusing to stop it automatically."
    Write-Host "Command line: $commandLine"
    exit 1
}

$descendants = @(Get-DescendantProcessIds -ParentPid ([int]$metadata.pid))
Stop-KnownPublisherProcesses -PreferredPids @($descendants + @([int]$metadata.pid))
Remove-Item -LiteralPath $pidFile -Force

Write-Host "Stopped AI publisher wrapper PID $($metadata.pid)."
if ($metadata.log_path) {
    Write-Host "Last log: $($metadata.log_path)"
}
if ($metadata.PSObject.Properties.Name -contains "display") {
    Write-Host "Display mode was: $([bool]$metadata.display)"
}
