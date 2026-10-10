#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
cd "$ROOT"
"$PYTHON" backend/tests/test_operations_40.py
"$PYTHON" backend/tests/test_components.py
"$PYTHON" backend/tests/test_migration_safety.py
"$PYTHON" backend/tests/test_rules_fuzz.py
"$PYTHON" backend/tests/make_ui_fixtures.py
cd frontend
npm ci --no-audit --no-fund
npm run lint
npm run build
npm exec -- esbuild tests/ui_verdict_test.tsx --bundle --platform=node --format=cjs --jsx=automatic --loader:.css=empty --external:jsdom --outfile=tests/.ui_test_out.cjs --log-level=error
trap 'rm -f tests/.ui_test_out.cjs tests/.sync_test_out.cjs tests/.component_sync_out.cjs tests/.building_out.cjs' EXIT
node tests/.ui_test_out.cjs
node tests/build_sync_test.mjs
node tests/.sync_test_out.cjs
npm exec -- esbuild tests/component_sync_test.tsx --bundle --platform=node --format=cjs --jsx=automatic --loader:.css=empty --external:jsdom '--define:import.meta.env={}' --outfile=tests/.component_sync_out.cjs --log-level=error
node tests/.component_sync_out.cjs
npm exec -- esbuild tests/building_test.tsx --bundle --platform=node --format=cjs --jsx=automatic --loader:.css=empty --external:jsdom '--define:import.meta.env={}' --outfile=tests/.building_out.cjs --log-level=error
node tests/.building_out.cjs
printf '%s\n' 'PASS: all local checks. Hosting/PostgreSQL/Gemini acceptance checks are documented separately.'
