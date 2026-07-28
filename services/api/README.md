# VMF Fantasy API

FastAPI backend and deterministic rule engine for the VMF Fantasy League.

## Local development

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
alembic upgrade head
uvicorn vmf_api.main:app --reload
```

Production uses `postgresql+asyncpg`. Tests override the database URL with
`sqlite+aiosqlite`.

Important environment variables:

```text
VMF_DATABASE_URL
VMF_ADMIN_API_KEY
VMF_CORS_ORIGINS
VMF_FPL_BASE_URL
```

The application never creates production tables at startup. Apply Alembic
migrations before starting the service.
