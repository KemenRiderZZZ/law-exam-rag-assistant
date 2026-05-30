@echo off
setlocal
chcp 65001 >nul

set "PS1_FILE=%~dpn0.ps1"

if not exist "%PS1_FILE%" (
  echo PowerShell script not found:
  echo %PS1_FILE%
  echo.
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1_FILE%" "%~1" "%~2" "%~3"
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if "%EXIT_CODE%"=="0" (
  echo Done.
) else (
  echo Failed. Exit code: %EXIT_CODE%
)
echo.
pause
exit /b %EXIT_CODE%
