@echo off
setlocal
set "ROOT=%~dp0.."
cd /d "%ROOT%"
if "%PYTHONPATH%"=="" set "PYTHONPATH=%ROOT%\src;%ROOT%\workers"
powershell -ExecutionPolicy Bypass -File "%ROOT%\scripts\run_desktop_windows.ps1" %*
exit /b %ERRORLEVEL%
