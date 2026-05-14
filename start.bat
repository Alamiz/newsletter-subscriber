@echo off
setlocal enabledelayedexpansion

echo.
echo ============================================================
echo   Newsletter Automation Tool - Startup
echo ============================================================
echo.

:: ---- Git pull ----
git pull 2>nul
if %errorlevel% neq 0 (
    echo [WARN] git pull failed or not a git repo - continuing
)

:: ---- Install / update Python dependencies ----
echo [*] Installing / updating dependencies...
python -m pip install -r requirements.txt --quiet --disable-pip-version-check
if %errorlevel% neq 0 (
    echo [ERROR] pip install failed. Ensure Python 3.11+ is in PATH.
    pause
    exit /b 1
)

:: ---- Fetch Camoufox browser binary (idempotent, skips if up to date) ----
echo [*] Checking Camoufox browser binary...
python -m camoufox fetch

:: ---- Ensure required input files exist ----
if not exist emails.txt (
    echo [ERROR] emails.txt not found.
    pause
    exit /b 1
)
if not exist newsletters.txt (
    echo [ERROR] newsletters.txt not found.
    pause
    exit /b 1
)

:: ---- Run ----
echo.
echo [*] Starting subscribe.py %*
echo.
python subscribe.py %*

echo.
echo [*] Done. Check output/ for results.
pause
