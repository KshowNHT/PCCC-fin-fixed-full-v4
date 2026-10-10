PCCC DOCKER FIX
===============

Files to replace/add in your project:

Project root:
  compose.yaml
  .env.example
  run-docker.bat
  stop-docker.bat
  logs-docker.bat

backend/
  Dockerfile

frontend/
  Dockerfile
  nginx.conf

IMPORTANT
---------
1. Your backend source must still have:
     backend/app/
     backend/data/
     backend/requirements.txt

2. Your frontend source must still have:
     frontend/package.json
     frontend source files

3. If you already have .env, do NOT overwrite it blindly.
   Compare it with this .env.example and ensure these variables exist:
     POSTGRES_PASSWORD
     JWT_SECRET
     GEMINI_API_KEY
     PCCC_ADMIN_USERNAME
     PCCC_ADMIN_PASSWORD
     MAX_STAFF_ACCOUNTS
     VITE_API_URL

4. Start:
     docker compose up -d --build
   or double-click:
     run-docker.bat

5. URLs:
     Frontend  http://localhost:5173
     Backend   http://localhost:8000
     Swagger   http://localhost:8000/docs
     Health    http://localhost:8000/api/health

6. Troubleshooting:
     docker compose ps
     docker compose logs -f postgres
     docker compose logs -f backend
     docker compose logs -f frontend

7. DO NOT run `docker compose down -v` unless you intentionally want to
   delete PostgreSQL and application persistent volumes.

WHY THE OLD CONFIG FAILED
-------------------------
- Backend actually listens on port 3000 in its Dockerfile, while old Compose
  mapped 8000:8000.
- Frontend production image uses Nginx port 80, while old Compose mapped
  5173:5173.
- Backend defaults DATABASE_URL to localhost:5432, which means "this backend
  container itself" when inside Docker.
- Old Compose had no PostgreSQL service and did not inject DATABASE_URL.
- VITE_API_URL was passed as a runtime environment variable, but Vite static
  builds need VITE_* variables at build time. The fixed Dockerfile uses ARG.
