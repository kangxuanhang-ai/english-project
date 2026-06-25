from fastapi import APIRouter, Depends

from app.dependencies import get_current_admin
from . import analytics, courses, dashboard, knowledge, orders, users

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/ping")
async def admin_ping(_admin: dict = Depends(get_current_admin)):
    return {"data": {"ok": True}, "code": 200, "message": "pong"}


router.include_router(dashboard.router)
router.include_router(users.router)
router.include_router(courses.router)
router.include_router(orders.router)
router.include_router(knowledge.router)
router.include_router(analytics.router)
