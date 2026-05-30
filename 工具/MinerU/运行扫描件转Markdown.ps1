$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$MinerURoot = "D:\Python\MinerU"
$MinerUExe = Join-Path $MinerURoot "venv\Scripts\mineru.exe"

$env:HF_HOME = Join-Path $MinerURoot "models\hf-cache"
$env:MODELSCOPE_CACHE = Join-Path $MinerURoot "models\ms-cache"
$env:MINERU_TOOLS_CONFIG_JSON = Join-Path $MinerURoot "mineru.json"
$env:MINERU_MODEL_SOURCE = "local"
$env:MINERU_PROCESSING_WINDOW_SIZE = "40"
$env:MINERU_PDF_RENDER_THREADS = "1"

if ($args.Count -lt 1) {
    Write-Host "Usage:" -ForegroundColor Yellow
    Write-Host '  run_mineru.bat "input file or folder" ["output folder"] [lang]'
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host '  run_mineru.bat "D:\docs\scan.pdf"'
    Write-Host '  run_mineru.bat "D:\docs\scan.pdf" "D:\docs\output"'
    Write-Host '  run_mineru.bat "D:\docs\scan.pdf" "D:\docs\output" ch'
    Write-Host ""
    Write-Host "Languages:" -ForegroundColor Yellow
    Write-Host "  ch      Chinese"
    Write-Host "  en      English"
    Write-Host "  japan   Japanese"
    Write-Host "  korean  Korean"
    Write-Host "  auto    Auto detect"
    exit 1
}

$InputPath = $args[0]
$OutputPath = if ($args.Count -ge 2 -and $args[1]) { $args[1] } else { Join-Path (Split-Path -Parent $InputPath) "MinerU-output" }
$OcrLang = if ($args.Count -ge 3 -and $args[2]) { $args[2] } else { "ch" }

if (!(Test-Path -LiteralPath $InputPath)) {
    Write-Host "Input path not found: $InputPath" -ForegroundColor Red
    exit 1
}

if (!(Test-Path -LiteralPath $MinerUExe)) {
    Write-Host "MinerU executable not found: $MinerUExe" -ForegroundColor Red
    exit 1
}

if (!(Test-Path -LiteralPath $OutputPath)) {
    New-Item -ItemType Directory -Path $OutputPath -Force | Out-Null
}

Write-Host ""
Write-Host "[MinerU] input: $InputPath" -ForegroundColor Cyan
Write-Host "[MinerU] output: $OutputPath" -ForegroundColor Cyan
Write-Host "[MinerU] lang: $OcrLang" -ForegroundColor Cyan
Write-Host "[MinerU] mode: pipeline + ocr" -ForegroundColor Cyan
Write-Host ""

& $MinerUExe -p $InputPath -o $OutputPath -b pipeline -m ocr -l $OcrLang
$ExitCode = $LASTEXITCODE

Write-Host ""
if ($ExitCode -eq 0) {
    Write-Host "Finished. Output: $OutputPath" -ForegroundColor Green
} else {
    Write-Host "Failed. Exit code: $ExitCode" -ForegroundColor Red
}

exit $ExitCode
