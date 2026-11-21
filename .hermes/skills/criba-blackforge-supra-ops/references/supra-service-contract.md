# SUPRA service contract

## Endpoint canónico
`http://127.0.0.1:<puerto efímero>` (arrancado por Shadow) o
`http://127.0.0.1:8080` (Docker/local dev).

## /health
- HTTP 200
- JSON: `{"status": "healthy", "service": "supra-agentic-taskmaster", "storage": {...}}`
- `health_ok()` valida además: scheme=http, hostname loopback, sin auth, path vacío, sin query/fragment, sin redirects.

## Env vars
Obligatorias (publicadas por Shadow antes de lanzar el server):
- `SUPRA_ENDPOINT` — URL del server
- `SUPRA_STORAGE_DIR` — directorio SQLite del artefacto
- `SUPRA_USE_MODEL=false` — desactiva llamadas al modelo

Opcionales:
- `SUPRA_API_TOKEN` — auth (service.py:41)
- `SUPRA_CORS_ORIGINS` — CORS
- `SUPRA_PROVIDER` — provider activo (default "hermes")

## Startup command real
- Docker: `uvicorn supra_agentic.service:app --host 0.0.0.0 --port 8080`
- Dev: `python -m uvicorn supra_agentic.service:app --host 127.0.0.1 --port 8080`
- Shadow (incrustado): `SupraServer` en thread daemon, free_port(), Config(host=127.0.0.1, port=<efímero>).
