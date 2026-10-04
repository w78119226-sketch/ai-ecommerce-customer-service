@echo off
setlocal
set "ROOT=%~dp0.."
cd /d "%ROOT%"
if "%CLAWBOT_DECISION_MODE%"=="" set "CLAWBOT_DECISION_MODE=deepseek"
if "%PYTHONPATH%"=="" set "PYTHONPATH=%ROOT%\src;%ROOT%\workers"
powershell -ExecutionPolicy Bypass -File "%ROOT%\scripts\run_dev_windows.ps1" %*
