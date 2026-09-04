@echo off
setlocal
title PCCC Docker - Start

cd /d "%~dp0"

echo ================================================
echo     PCCC APPLICATION - DOCKER START
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

if not exist "compose.yaml" (
    echo [ERROR] compose.yaml was not found next to this file.
    pause
    exit /b 1
)

if not exist ".env" (
    if exist ".env.example" (
        copy /Y ".env.example" ".env" >nul
        echo [INFO] Created .env from .env.example
        echo [INFO] For AI features, add GEMINI_API_KEY to .env.
        echo [WARNING] Before real use: also change JWT_SECRET and
        echo [WARNING] PCCC_ADMIN_PASSWORD in .env - the backend will
        echo [WARNING] REFUSE TO START with the default values shipped
        echo [WARNING] in .env.example (this is intentional, for safety).
        echo.
    )
)

echo [1/4] Validating compose.yaml...
docker compose config >nul
if errorlevel 1 (
    echo [ERROR] Invalid compose.yaml.
    docker compose config
    pause
    exit /b 1
)

echo [2/4] Building and starting PostgreSQL, backend and frontend...
docker compose up -d --build
if errorlevel 1 (
    echo [ERROR] Docker Compose failed.
    docker compose logs --tail=100
    pause
    exit /b 1
)

echo [3/4] Current container status:
docker compose ps
echo.

echo [4/4] Waiting briefly for services...
timeout /t 5 /nobreak >nul
docker compose ps
echo.

echo ================================================
echo Application URLs
echo ================================================
echo Frontend : http://localhost:5173
echo Backend  : http://localhost:8000
echo API Docs : http://localhost:8000/docs
echo Health   : http://localhost:8000/api/health
echo.
echo If something fails, run: docker compose logs -f
echo.

start "" "http://localhost:5173"
pause
endlocal
