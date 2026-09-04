@echo off
cd /d "%~dp0"
echo Stopping PCCC Docker application...
docker compose down
echo.
echo Containers stopped. Database/data volumes were NOT deleted.
pause
