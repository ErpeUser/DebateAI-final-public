@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-DebateAI.ps1" %*
exit /b %ERRORLEVEL%
