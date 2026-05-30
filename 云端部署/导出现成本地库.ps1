param(
  [string]$ProjectRoot = "D:\桌面\云端法考知识问答项目",
  [string]$OutputDir = "",
  [string]$DumpFileName = "lawqa.dump"
)

$dbDir = Join-Path $ProjectRoot "数据库"
$envFile = Join-Path $dbDir ".env.pg"

if (-not (Test-Path -LiteralPath $envFile)) {
  throw ".env.pg not found: $envFile"
}

$envMap = @{}
Get-Content -LiteralPath $envFile | ForEach-Object {
  if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
  $parts = $_.Split('=', 2)
  $envMap[$parts[0].Trim()] = $parts[1].Trim()
}

$host = if ($envMap.ContainsKey('POSTGRES_HOST')) { $envMap['POSTGRES_HOST'] } else { '127.0.0.1' }
$port = if ($envMap.ContainsKey('POSTGRES_PORT')) { $envMap['POSTGRES_PORT'] } else { '5432' }
$db   = if ($envMap.ContainsKey('POSTGRES_DB')) { $envMap['POSTGRES_DB'] } else { 'lawqa' }
$user = if ($envMap.ContainsKey('POSTGRES_USER')) { $envMap['POSTGRES_USER'] } else { 'law' }
$pass = if ($envMap.ContainsKey('POSTGRES_PASSWORD')) { $envMap['POSTGRES_PASSWORD'] } else { 'law123456' }

if (-not $OutputDir) {
  $OutputDir = Join-Path $ProjectRoot "云端部署\exports"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
$dumpPath = Join-Path $OutputDir $DumpFileName

$env:PGPASSWORD = $pass
try {
  pg_dump -h $host -p $port -U $user -d $db -Fc -f $dumpPath
} finally {
  Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}

Write-Host "Exported database dump to: $dumpPath" -ForegroundColor Green
