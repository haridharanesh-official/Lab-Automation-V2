param([Parameter(Mandatory=$true)][string]$Image)
$env:PYTHONPATH = "ai-pc"
.\.venv\Scripts\python.exe ai-pc\tools\zone_editor.py $Image --output config\zones.json

