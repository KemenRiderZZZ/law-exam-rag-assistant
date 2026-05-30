$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = "C:\Users\Redmi\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$script = Get-ChildItem -Path $projectRoot -Recurse -Filter "search_web_server.py" | Select-Object -First 1 -ExpandProperty FullName

if (-not (Test-Path -LiteralPath $python)) {
    throw "Python runtime not found: $python"
}

if (-not $script) {
    throw "search_web_server.py not found under: $projectRoot"
}

$dbDir = Split-Path -Parent $script
Set-Location -LiteralPath $dbDir

Write-Host "App URL: http://127.0.0.1:8765" -ForegroundColor Green
Write-Host "Starting local law exam chat service. Keep this window open." -ForegroundColor Yellow
Write-Host ""

& $python -u $script --host 127.0.0.1 --port 8765
