@echo off
setlocal

set "REPO_ROOT=%~dp0"
cd /d "%REPO_ROOT%"

powershell.exe -NoExit -ExecutionPolicy Bypass -File "%REPO_ROOT%web\backend\scripts\run_local_windows.ps1"
