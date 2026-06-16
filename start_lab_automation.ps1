[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$Display
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

$pythonPath = Join-Path $repoRoot ".venv\Scripts\python.exe"
$configPath = Join-Path $repoRoot "config\config.yaml"
$zonesPath = Join-Path $repoRoot "config\zones.json"
$modelPath = Join-Path $repoRoot "models\backcam_yolov8s_improved_v3_hardfp.pt"
$mainPath = Join-Path $repoRoot "ai-pc\src\main.py"
$logDir = Join-Path $repoRoot "logs\ai-publisher"
$pidFile = Join-Path $logDir "ai-publisher.pid.json"

function Write-Section([string]$Title) {
    Write-Host ""
    Write-Host "== $Title ==" -ForegroundColor Cyan
}

function Fail([string]$Message) {
    Write-Error $Message
    exit 1
}

function Assert-File([string]$Path, [string]$Label) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        Fail "$Label missing: $Path"
    }
    Write-Host "[OK] $Label -> $Path" -ForegroundColor Green
}

function Test-TcpEndpoint([string]$HostName, [int]$Port, [int]$TimeoutMs = 3000) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $async = $client.BeginConnect($HostName, $Port, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne($TimeoutMs, $false)) {
            return $false
        }
        $client.EndConnect($async) | Out-Null
        return $true
    } catch {
        return $false
    } finally {
        $client.Close()
    }
}

function Get-ConfigValues {
    $mode = $null
    $cameraUrl = $null
    $mqttHost = $null
    $mqttPort = $null
    $heartbeatSeconds = $null
    $section = ""

    foreach ($line in Get-Content -LiteralPath $configPath) {
        if ($line -match '^(?<key>[A-Za-z0-9_]+):\s*(?<value>.*)$') {
            $key = $matches.key
            $value = $matches.value.Trim()
            if ($value -eq "") {
                $section = $key
                continue
            }
            $section = ""
            switch ($key) {
                "mode" { $mode = $value }
                "heartbeat_seconds" { $heartbeatSeconds = [double]$value }
            }
            continue
        }

        if ($line -match '^\s+(?<key>[A-Za-z0-9_]+):\s*(?<value>.*)$') {
            $key = $matches.key
            $value = $matches.value.Trim()
            switch ($section) {
                "camera" {
                    if ($key -eq "url") { $cameraUrl = $value }
                }
                "mqtt" {
                    if ($key -eq "host") { $mqttHost = $value }
                    if ($key -eq "port") { $mqttPort = [int]$value }
                }
            }
        }
    }

    if (-not $mode -or -not $cameraUrl -or -not $mqttHost -or -not $mqttPort) {
        Fail "Unable to parse required values from config/config.yaml"
    }
    if (-not $heartbeatSeconds) {
        $heartbeatSeconds = 10
    }
    return [pscustomobject]@{
        mqtt_host = $mqttHost
        mqtt_port = $mqttPort
        camera_url = $cameraUrl
        mode = $mode
        heartbeat_seconds = $heartbeatSeconds
    }
}

function Test-CameraStream([string]$CameraUrl) {
    $ffprobe = Get-Command ffprobe -ErrorAction SilentlyContinue
    if (-not $ffprobe) {
        Fail "ffprobe is not available on PATH, so camera validation cannot continue safely."
    }
    $args = @(
        "-v", "error",
        "-rtsp_transport", "tcp",
        "-select_streams", "v:0",
        "-show_entries", "stream=codec_name,width,height,avg_frame_rate",
        "-of", "json",
        $CameraUrl
    )
    $output = & $ffprobe.Source @args 2>&1
    if ($LASTEXITCODE -ne 0) {
        Fail "Camera stream check failed for $CameraUrl`n$output"
    }
    $parsed = $output | ConvertFrom-Json
    if (-not $parsed.streams -or $parsed.streams.Count -lt 1) {
        Fail "Camera stream opened but ffprobe did not return a video stream for $CameraUrl."
    }
    $stream = $parsed.streams[0]
    $fps = $stream.avg_frame_rate
    Write-Host "[OK] Camera stream -> codec=$($stream.codec_name) size=$($stream.width)x$($stream.height) fps=$fps" -ForegroundColor Green
}

function Get-MqttSnapshot([string]$HostName, [int]$Port) {
    $mosquittoSub = Get-Command mosquitto_sub -ErrorAction SilentlyContinue
    if (-not $mosquittoSub) {
        Write-Warning "mosquitto_sub is not installed on this AI PC, so retained topic snapshots are unavailable."
        return $null
    }
    try {
        $modeState = & $mosquittoSub.Source -h $HostName -p $Port -C 1 -W 2 -t "lab/automation/mode_state" 2>$null
        $heartbeatRaw = & $mosquittoSub.Source -h $HostName -p $Port -C 1 -W 2 -t "lab/vision/heartbeat" 2>$null
        $heartbeatAge = $null
        $heartbeat = $null
        if ($heartbeatRaw) {
            $heartbeat = $heartbeatRaw | ConvertFrom-Json -ErrorAction SilentlyContinue
            if ($heartbeat -and $heartbeat.timestamp) {
                $heartbeatTime = [DateTimeOffset]::FromUnixTimeSeconds([int64]$heartbeat.timestamp).LocalDateTime
                $heartbeatAge = [math]::Round((New-TimeSpan -Start $heartbeatTime -End (Get-Date)).TotalSeconds, 3)
            }
        }
        return [pscustomobject]@{
            mode_state = $modeState
            mode_state_age_seconds = $null
            vision_heartbeat = $heartbeat
            vision_heartbeat_age_seconds = $heartbeatAge
        }
    } catch {
        Write-Warning "MQTT topic snapshot could not be collected."
        return $null
    }
}

function Get-ExistingPublisherMetadata {
    if (-not (Test-Path -LiteralPath $pidFile -PathType Leaf)) {
        return $null
    }
    try {
        $metadata = Get-Content -LiteralPath $pidFile -Raw | ConvertFrom-Json
    } catch {
        Write-Warning "PID file exists but could not be parsed: $pidFile"
        return $null
    }
    if (-not $metadata.pid) {
        return $null
    }
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $($metadata.pid)" -ErrorAction SilentlyContinue
    if (-not $process) {
        return $null
    }
    return [pscustomobject]@{
        Pid = [int]$metadata.pid
        StartedAt = $metadata.started_at
        LogPath = $metadata.log_path
        Display = [bool]$metadata.display
        CommandLine = $process.CommandLine
    }
}

Write-Section "Repo Root"
Write-Host $repoRoot

Write-Section "Required Files"
Assert-File $pythonPath "Python venv interpreter"
Assert-File $configPath "Runtime config"
Assert-File $zonesPath "Zone map"
Assert-File $modelPath "Production model"
Assert-File $mainPath "AI publisher entrypoint"

$config = Get-ConfigValues
if ($config.mode.ToLowerInvariant() -ne "monitor") {
    Fail "config/config.yaml must keep mode=monitor for this startup path. Current value: $($config.mode)"
}

Write-Section "Network Checks"
if (-not (Test-TcpEndpoint -HostName $config.mqtt_host -Port $config.mqtt_port)) {
    Fail "MQTT broker is unreachable at $($config.mqtt_host):$($config.mqtt_port)"
}
Write-Host "[OK] MQTT broker reachable -> $($config.mqtt_host):$($config.mqtt_port)" -ForegroundColor Green
Test-CameraStream -CameraUrl $config.camera_url

Write-Section "Live Topic Snapshot"
$snapshot = Get-MqttSnapshot -HostName $config.mqtt_host -Port $config.mqtt_port
if ($snapshot) {
    $modeState = if ($snapshot.mode_state) { $snapshot.mode_state } else { "unavailable" }
    $heartbeatAge = if ($null -ne $snapshot.vision_heartbeat_age_seconds) { "$($snapshot.vision_heartbeat_age_seconds)s" } else { "unavailable" }
    Write-Host "[INFO] lab/automation/mode_state -> $modeState"
    Write-Host "[INFO] lab/vision/heartbeat age -> $heartbeatAge"
} else {
    Write-Host "[WARN] Could not read retained live topics. Startup can continue because mode authority stays on Home Assistant/Node-RED." -ForegroundColor Yellow
}

$existing = Get-ExistingPublisherMetadata
if ($existing) {
    Write-Section "Publisher Status"
    Write-Host "[OK] AI publisher already running (PID $($existing.Pid))" -ForegroundColor Green
    Write-Host "Started: $($existing.StartedAt)"
    Write-Host "Log: $($existing.LogPath)"
    Write-Host "Display mode: $($existing.Display)"
    exit 0
}

if ($DryRun) {
    Write-Section "Dry Run"
    Write-Host "[OK] Dry-run checks passed. Publisher was not started." -ForegroundColor Green
    exit 0
}

New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logPath = Join-Path $logDir "$timestamp.log"
$displayArg = if ($Display) { " --display" } else { "" }
$runnerCommand = "& '$pythonPath' -m src.main --config 'config/config.yaml'$displayArg *>> '$logPath'"

Write-Section "Start Publisher"
$env:PYTHONPATH = "ai-pc"
$process = Start-Process -FilePath "powershell.exe" `
    -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $runnerCommand) `
    -WorkingDirectory $repoRoot `
    -WindowStyle $(if ($Display) { "Normal" } else { "Hidden" }) `
    -PassThru

$metadata = [pscustomobject]@{
    pid = $process.Id
    started_at = (Get-Date).ToString("s")
    log_path = $logPath
    display = [bool]$Display
}
$metadata | ConvertTo-Json | Set-Content -LiteralPath $pidFile

Write-Host "[OK] AI publisher started with wrapper PID $($process.Id)" -ForegroundColor Green
Write-Host "Log: $logPath"
Write-Host "Display mode: $([bool]$Display)"
if ($Display) {
    Write-Host "A live OpenCV overlay window will open in the launched publisher session. Close it with 'q' or Ctrl+C." -ForegroundColor Green
}
Write-Host "Mode remains under Home Assistant / Node-RED control. This script did not change automation mode." -ForegroundColor Yellow
