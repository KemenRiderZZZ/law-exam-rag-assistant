@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PYTHON_EXE=C:\Users\Redmi\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
set "SCRIPT_FILE=%SCRIPT_DIR%search_web_server.py"

if not exist "%PYTHON_EXE%" (
  echo Python runtime not found:
  echo %PYTHON_EXE%
  pause
  exit /b 1
)

if not exist "%SCRIPT_FILE%" (
  echo search_web_server.py not found:
  echo %SCRIPT_FILE%
  pause
  exit /b 1
)

cd /d "%SCRIPT_DIR%"
echo Page: http://127.0.0.1:8765
echo Starting search_web_server.py...
echo Keep this window open.
echo.

"%PYTHON_EXE%" -u "%SCRIPT_FILE%" --host 127.0.0.1 --port 8765
