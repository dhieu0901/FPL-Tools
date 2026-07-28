from fastapi import APIRouter

from vmf_api.api.routes import admin, classic, cups, h2h, managers

api_router = APIRouter()
api_router.include_router(managers.router)
api_router.include_router(classic.router)
api_router.include_router(h2h.router)
api_router.include_router(cups.router)
api_router.include_router(admin.router)
