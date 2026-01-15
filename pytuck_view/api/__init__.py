"""API 路由入口。

app.py 会 include_router(..., prefix="/api")。
此处只负责聚合子路由。
"""

from fastapi import APIRouter

from .files import router as files_router
from .tables import router as tables_router

router = APIRouter()
router.include_router(files_router)
router.include_router(tables_router)
