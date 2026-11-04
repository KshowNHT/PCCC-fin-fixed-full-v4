@echo off
cd /d "%~dp0"
echo Stopping PCCC Local Docker application...
docker compose -f compose.local.yaml down
echo.
echo Containers stopped. Database/data volumes were NOT deleted.
pause
