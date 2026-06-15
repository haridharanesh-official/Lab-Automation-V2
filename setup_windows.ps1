$ErrorActionPreference = "Stop"
if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw "Install Python 3.11 first." }
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
Copy-Item config\config.example.yaml config\config.yaml -ErrorAction SilentlyContinue
Write-Host "Setup complete. System remains in Manual/Monitor until explicitly configured."

