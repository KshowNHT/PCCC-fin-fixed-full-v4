@echo off
setlocal
title PCCC Docker - Start (Local 1-Click)

cd /d "%~dp0"

echo ================================================
echo     PCCC APPLICATION - DOCKER 1-CLICK START
echo ================================================
echo.

where docker >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker CLI was not found.
    echo Install Docker Desktop first.
    pause
    exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Desktop / Docker Engine is not running.
    echo Open Docker Desktop and wait until it is ready.
    pause
    exit /b 1
)

if not exist "compose.local.yaml" (
    echo [ERROR] compose.local.yaml was not found next to this file.
    pause
    exit /b 1
)

if not exist ".env" (
    if not exist "backend\.env" (
        echo [INFO] Using built-in local defaults (Admin: admin / admin123).
        echo [INFO] For AI features, add GEMINI_API_KEY to backend/.env or .env.
        echo.
    )
)

echo [1/4] Validating compose.local.yaml...
docker compose -f compose.local.yaml config >nul
if errorlevel 1 (
    echo [ERROR] Invalid compose.local.yaml.
    docker compose -f compose.local.yaml config
    pause
    exit /b 1
)

echo [2/4] Building and starting PostgreSQL, backend and frontend...
docker compose -f compose.local.yaml up -d --build
if errorlevel 1 (
    echo [ERROR] Docker Compose failed.
    docker compose -f compose.local.yaml logs --tail=100
    pause
    exit /b 1
)

echo [3/4] Current container status:
docker compose -f compose.local.yaml ps
echo.

echo [4/4] Waiting briefly for services...
timeout /t 5 /nobreak >nul
docker compose -f compose.local.yaml ps
echo.

echo ================================================
echo Application URLs
echo ================================================
echo Frontend : http://localhost:5173
echo Backend  : http://localhost:8000
echo API Docs : http://localhost:8000/docs
echo Health   : http://localhost:8000/api/health
echo Default Admin Login: admin / admin123 (unless customized in .env)
echo.
echo If something fails, run: docker compose -f compose.local.yaml logs -f
echo.

start "" "http://localhost:5173"
pause
endlocal
