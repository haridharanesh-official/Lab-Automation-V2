[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

$pythonPath = Join-Path $repoRoot ".venv\Scripts\python.exe"
$configPath = Join-Path $repoRoot "config\config.yaml"
$pidFile = Join-Path $repoRoot "logs\ai-publisher\ai-publisher.pid.json"

function Test-TcpEndpoint([string]$HostName, [int]$Port, [int]$TimeoutMs = 3000) {
    $timeoutSeconds = [math]::Ceiling($TimeoutMs / 1000.0)
    $script = "import socket,sys; socket.create_connection((r'$HostName',$Port), timeout=$timeoutSeconds).close(); print('OK')"
    try {
        $result = & .\.venv\Scripts\python.exe -c $script 2>$null
        return $LASTEXITCODE -eq 0 -and $result -eq "OK"
    } catch {
        return $false
    }
}

function Get-ConfigValues {
    $cameraUrl = $null
    $mqttHost = $null
    $mqttPort = $null
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

    if (-not $cameraUrl -or -not $mqttHost -or -not $mqttPort) {
        throw "Unable to parse config/config.yaml"
    }

    return [pscustomobject]@{
        mqtt_host = $mqttHost
        mqtt_port = $mqttPort
        camera_url = $cameraUrl
    }
}

function Get-MqttSnapshot([string]$HostName, [int]$Port) {
    $mosquittoSub = Get-Command mosquitto_sub -ErrorAction SilentlyContinue
    if (-not $mosquittoSub) {
        return $null
    }
    try {
        $modeState = & $mosquittoSub.Source -h $HostName -p $Port -C 1 -W 2 -t "lab/automation/mode_state" 2>$null
        $heartbeatRaw = & $mosquittoSub.Source -h $HostName -p $Port -C 1 -W 2 -t "lab/vision/heartbeat" 2>$null
        $heartbeatAge = $null
        if ($heartbeatRaw) {
            $heartbeat = $heartbeatRaw | ConvertFrom-Json -ErrorAction SilentlyContinue
            if ($heartbeat -and $heartbeat.timestamp) {
                $heartbeatTime = [DateTimeOffset]::FromUnixTimeSeconds([int64]$heartbeat.timestamp).LocalDateTime
                $heartbeatAge = [math]::Round((New-TimeSpan -Start $heartbeatTime -End (Get-Date)).TotalSeconds, 3)
            }
        }
        return [pscustomobject]@{
            mode_state = $modeState
            heartbeat_age_seconds = $heartbeatAge
        }
    } catch {
        return $null
    }
}

$config = Get-ConfigValues
$cameraUri = [Uri]$config.camera_url
$cameraReachable = Test-TcpEndpoint -HostName $cameraUri.Host -Port $cameraUri.Port
$mqttReachable = Test-TcpEndpoint -HostName $config.mqtt_host -Port $config.mqtt_port
$snapshot = $null
if ($mqttReachable) {
    $snapshot = Get-MqttSnapshot -HostName $config.mqtt_host -Port $config.mqtt_port
}

$publisherRunning = $false
$publisherPid = $null
$logPath = $null
$displayMode = $null
if (Test-Path -LiteralPath $pidFile -PathType Leaf) {
    $metadata = Get-Content -LiteralPath $pidFile -Raw | ConvertFrom-Json
    if ($metadata.pid) {
        $process = Get-CimInstance Win32_Process -Filter "ProcessId = $($metadata.pid)" -ErrorAction SilentlyContinue
        if ($process) {
            $publisherRunning = $true
            $publisherPid = $metadata.pid
            $logPath = $metadata.log_path
            if ($metadata.PSObject.Properties.Name -contains "display") {
                $displayMode = [bool]$metadata.display
            }
        }
    }
}

[pscustomobject]@{
    camera_url = $config.camera_url
    camera_reachable = $cameraReachable
    mqtt_host = $config.mqtt_host
    mqtt_port = $config.mqtt_port
    mqtt_reachable = $mqttReachable
    latest_mode_state = if ($snapshot) { $snapshot.mode_state } else { $null }
    latest_vision_heartbeat_age_seconds = if ($snapshot) { $snapshot.heartbeat_age_seconds } else { $null }
    ai_publisher_running = $publisherRunning
    ai_publisher_pid = $publisherPid
    ai_publisher_log = $logPath
    ai_publisher_display = $displayMode
} | Format-List
