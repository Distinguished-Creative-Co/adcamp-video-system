@echo off
rem AdCamp Video System for Windows: runs the AVS launcher (tools\avs.py) on AVS's own Python.
setlocal
set "AVS_ROOT=%~dp0"
if not exist "%AVS_ROOT%runtime\base\Scripts\python.exe" (
  echo AVS is not set up yet on this PC. Run bootstrap.ps1 in the AVS folder first.
  exit /b 1
)
"%AVS_ROOT%runtime\base\Scripts\python.exe" "%AVS_ROOT%tools\avs.py" %*
exit /b %errorlevel%
