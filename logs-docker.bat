@echo off
cd /d "%~dp0"
docker compose -f compose.local.yaml logs -f --tail=200
