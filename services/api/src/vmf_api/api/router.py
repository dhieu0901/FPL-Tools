from fastapi import APIRouter

from vmf_api.api.routes import admin, classic, cron, cups, fpl, h2h, highlights, managers

api_router = APIRouter()
api_router.include_router(managers.router)
api_router.include_router(classic.router)
api_router.include_router(h2h.router)
api_router.include_router(cups.router)
api_router.include_router(fpl.router)
api_router.include_router(highlights.router)
api_router.include_router(cron.router)
api_router.include_router(admin.router)
