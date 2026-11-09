@echo off
setlocal

set "SONIQ_ROOT=%~dp0"
pushd "%SONIQ_ROOT%"
if errorlevel 1 (
  echo ERROR: Could not enter the SONIQ project directory.
  pause
  exit /b 1
)

set "SONIQ_PYTHON="
set "SONIQ_ROOT_PYTHON=%SONIQ_ROOT%.venv\Scripts\python.exe"
set "SONIQ_ML_PYTHON=%SONIQ_ROOT%ml\.venv\Scripts\python.exe"

if exist "%SONIQ_ROOT_PYTHON%" (
  "%SONIQ_ROOT_PYTHON%" -c "import sys" >nul 2>&1
  if not errorlevel 1 set "SONIQ_PYTHON=%SONIQ_ROOT_PYTHON%"
)
if not defined SONIQ_PYTHON if exist "%SONIQ_ML_PYTHON%" (
  "%SONIQ_ML_PYTHON%" -c "import sys" >nul 2>&1
  if not errorlevel 1 set "SONIQ_PYTHON=%SONIQ_ML_PYTHON%"
)

if not defined SONIQ_PYTHON (
  echo ERROR: No usable project virtual environment was found.
  echo Create one with: py -3 -m venv .venv
  echo Then install project requirements with:
  echo   .\.venv\Scripts\python.exe -m pip install -r ml\requirements.txt -r backend\requirements.txt
  echo Existing environments are left unchanged.
  popd
  pause
  exit /b 1
)

"%SONIQ_PYTHON%" -c "import backend.app" >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python cannot import the SONIQ backend from the project root.
  echo Check the environment and install only the listed project requirements if needed.
  popd
  pause
  exit /b 1
)

echo Python interpreter: %SONIQ_PYTHON%
echo Starting static dashboard at http://127.0.0.1:8001/
start "SONIQ Dashboard" "%SONIQ_PYTHON%" -m http.server 8001 --bind 127.0.0.1 --directory "%SONIQ_ROOT%dashboard"
if errorlevel 1 (
  echo ERROR: Could not start the dashboard server.
  popd
  pause
  exit /b 1
)

echo Starting backend in this window. Press Ctrl+C to stop it.
"%SONIQ_PYTHON%" "%SONIQ_ROOT%backend\start_backend.py"
set "SONIQ_EXIT_CODE=%ERRORLEVEL%"
if not "%SONIQ_EXIT_CODE%"=="0" (
  echo Backend exited with code %SONIQ_EXIT_CODE%.
  echo The dashboard server remains open in its separate window.
  pause
)

popd
exit /b %SONIQ_EXIT_CODE%
