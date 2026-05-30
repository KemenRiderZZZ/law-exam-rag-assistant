$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$projectRoot = Split-Path -Parent $PSScriptRoot
$logDir = Join-Path $projectRoot "codex-cleanup-logs"
$logPath = Join-Path $logDir "codex-cache-cleanup.log"
$statePath = Join-Path $logDir "codex-cache-cleanup-state.json"
$minIntervalDays = 7

function Write-Log {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }
    Add-Content -Path $logPath -Value $line -Encoding UTF8
    Write-Output $line
}

function Read-State {
    if (-not (Test-Path $statePath)) {
        return $null
    }

    try {
        return Get-Content -Raw $statePath | ConvertFrom-Json
    }
    catch {
        Write-Log "WARN Failed to read cleanup state, continuing with fresh state."
        return $null
    }
}

function Write-State {
    param(
        [datetime]$LastSuccessAt,
        [string]$BackupPath
    )

    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }

    $payload = [PSCustomObject]@{
        lastSuccessAt = $LastSuccessAt.ToString("o")
        backupPath    = $BackupPath
    }

    $payload | ConvertTo-Json | Set-Content -Path $statePath -Encoding UTF8
}

try {
    $state = Read-State
    if ($state -and $state.lastSuccessAt) {
        $lastSuccess = [datetime]::Parse($state.lastSuccessAt)
        $elapsed = (Get-Date) - $lastSuccess
        if ($elapsed.TotalDays -lt $minIntervalDays) {
            Write-Log ("SKIP Last successful cleanup was {0:N1} days ago, below the {1}-day interval." -f $elapsed.TotalDays, $minIntervalDays)
            exit 0
        }
    }

    $running = Get-Process Codex -ErrorAction SilentlyContinue
    if ($running) {
        Write-Log "SKIP Codex is running, cleanup postponed."
        exit 0
    }

    $codexRoot = Join-Path $env:LOCALAPPDATA "Packages\OpenAI.Codex_2p2nqsd0c76g0\LocalCache\Roaming\Codex"
    if (-not (Test-Path $codexRoot)) {
        Write-Log "SKIP Codex cache root was not found: $codexRoot"
        exit 0
    }

    $partitionRoot = Join-Path $codexRoot "Partitions\codex-browser-app"
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $backupRoot = Join-Path $codexRoot ("backup-reset-" + $timestamp)

    $targets = @(
        (Join-Path $codexRoot "Cache"),
        (Join-Path $codexRoot "Code Cache"),
        (Join-Path $codexRoot "GPUCache"),
        (Join-Path $codexRoot "DawnGraphiteCache"),
        (Join-Path $codexRoot "DawnWebGPUCache"),
        (Join-Path $codexRoot "blob_storage"),
        (Join-Path $codexRoot "Session Storage"),
        (Join-Path $codexRoot "Shared Dictionary"),
        (Join-Path $codexRoot "Preferences"),
        (Join-Path $codexRoot "Local State"),
        (Join-Path $partitionRoot "Cache"),
        (Join-Path $partitionRoot "Code Cache"),
        (Join-Path $partitionRoot "GPUCache"),
        (Join-Path $partitionRoot "DawnGraphiteCache"),
        (Join-Path $partitionRoot "DawnWebGPUCache"),
        (Join-Path $partitionRoot "blob_storage"),
        (Join-Path $partitionRoot "Session Storage"),
        (Join-Path $partitionRoot "Shared Dictionary"),
        (Join-Path $partitionRoot "Preferences")
    )

    $existingTargets = @($targets | Where-Object { Test-Path $_ })
    if ($existingTargets.Count -eq 0) {
        Write-Log "SKIP No cleanup targets were found."
        exit 0
    }

    New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null

    $moved = New-Object System.Collections.Generic.List[string]
    foreach ($path in $existingTargets) {
        $relative = $path.Substring($codexRoot.Length).TrimStart('\')
        $destination = Join-Path $backupRoot $relative
        $destinationParent = Split-Path $destination -Parent
        if (-not (Test-Path $destinationParent)) {
            New-Item -ItemType Directory -Path $destinationParent -Force | Out-Null
        }
        Move-Item -LiteralPath $path -Destination $destination -Force
        $moved.Add($relative)
    }

    $backups = Get-ChildItem $codexRoot -Directory -Force |
        Where-Object { $_.Name -like "backup-reset-*" } |
        Sort-Object LastWriteTime -Descending

    $oldBackups = $backups | Select-Object -Skip 3
    foreach ($oldBackup in $oldBackups) {
        Remove-Item -LiteralPath $oldBackup.FullName -Recurse -Force
        Write-Log ("PRUNE removed old backup {0}" -f $oldBackup.Name)
    }

    Write-Log ("DONE Cleaned {0} targets. Backup: {1}" -f $moved.Count, $backupRoot)
    Write-Log ("DETAIL " + ($moved -join ", "))
    Write-State -LastSuccessAt (Get-Date) -BackupPath $backupRoot
    exit 0
}
catch {
    Write-Log ("ERROR " + $_.Exception.Message)
    exit 1
}
