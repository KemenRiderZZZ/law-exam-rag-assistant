$ErrorActionPreference = "Stop"

$pgRoot = "D:\PostgreSQL\16"
$psql = Join-Path $pgRoot "bin\psql.exe"
$initSql = Join-Path (Join-Path $PSScriptRoot "init") "01-init-pgvector.sql"

$repoParent = Get-ChildItem -LiteralPath $PSScriptRoot -Directory |
    Where-Object { Test-Path (Join-Path $_.FullName "pgvector-src\pgvector") } |
    Select-Object -First 1

if (-not $repoParent) {
    throw "pgvector source parent directory not found under script root."
}

$repoDir = Join-Path $repoParent.FullName "pgvector-src\pgvector"

if (-not (Test-Path $repoDir)) {
    throw "pgvector source directory not found: $repoDir"
}

if (-not (Test-Path $psql)) {
    throw "psql not found: $psql"
}

Copy-Item -LiteralPath (Join-Path $repoDir "vector.dll") -Destination (Join-Path $pgRoot "lib\vector.dll") -Force
Copy-Item -LiteralPath (Join-Path $repoDir "vector.control") -Destination (Join-Path $pgRoot "share\extension\vector.control") -Force
Copy-Item -Path (Join-Path $repoDir "sql\vector--*.sql") -Destination (Join-Path $pgRoot "share\extension") -Force

$env:PGPASSWORD = "please-change-this-password"

& $psql -h 127.0.0.1 -p 5432 -U postgres -d lawqa -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS vector;"
& $psql -h 127.0.0.1 -p 5432 -U postgres -d lawqa -v ON_ERROR_STOP=1 -f $initSql
& $psql -h 127.0.0.1 -p 5432 -U postgres -d lawqa -c "SELECT extname, extversion FROM pg_extension;"

Write-Host ""
Write-Host "pgvector installed and enabled."
Write-Host "Next step: import JSONL chunks."
