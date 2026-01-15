"""文件相关 API 路由

包含：
- 最近文件
- 发现文件
- 打开文件（本地路径）
- 关闭文件 / 删除历史

统一前缀由 app.include_router(..., prefix="/api") 提供。
"""
import asyncio
from pathlib import Path

from fastapi import APIRouter, Query
from pydantic import BaseModel

from ..services.database import DatabaseService
from ..services.file_manager import file_manager
from .schemas import ApiResponse, Empty, fail, ok

router = APIRouter()

# 全局数据库服务实例字典（按 file_id 存储）
db_services: dict[str, DatabaseService] = {}

# 全局当前文件 ID（兼容性逻辑已废弃，但当前仍用于内部管理）
current_file_id: str | None = None
_current_file_lock = asyncio.Lock()


@router.get(
    "/recent-files",
    summary="获取最近打开的文件列表",
    response_model=ApiResponse[dict],
)
async def get_recent_files() -> ApiResponse[dict]:
    try:
        recent_files = file_manager.get_recent_files(limit=10)
        files_data = [
            {
                "file_id": f.file_id,
                "path": f.path,
                "name": f.name,
                "last_opened": f.last_opened,
                "file_size": f.file_size,
                "engine_name": f.engine_name,
            }
            for f in recent_files
        ]
        return ok(data={"files": files_data}, msg="获取最近文件列表成功")
    except Exception as e:
        return fail(msg=f"获取最近文件列表失败: {e}")


@router.get(
    "/discover-files",
    summary="发现指定目录中的 pytuck 文件",
    response_model=ApiResponse[dict],
)
async def discover_files(directory: str | None = Query(None)) -> ApiResponse[dict]:
    try:
        discovered = file_manager.discover_files(directory)
        return ok(data={"files": discovered}, msg="文件扫描成功")
    except Exception as e:
        return fail(msg=f"文件扫描失败: {e}")


class OpenFileBody(BaseModel):
    path: str


@router.post(
    "/open-file",
    summary="打开数据库文件",
    response_model=ApiResponse[dict],
)
async def open_file(request: OpenFileBody) -> ApiResponse[dict]:
    try:
        file_record = file_manager.open_file(request.path)
        if not file_record:
            return fail(code=1, msg="无法打开文件")

        db_service = DatabaseService()
        success = db_service.open_database(request.path)
        if not success:
            return fail(code=1, msg="数据库打开失败")

        db_services[file_record.file_id] = db_service

        data = {
            "file_id": file_record.file_id,
            "name": file_record.name,
            "path": file_record.path,
            "file_size": file_record.file_size,
            "engine_name": file_record.engine_name,
        }
        return ok(data=data, msg="数据库打开成功")
    except ValueError as e:
        return fail(code=1, msg=str(e))
    except Exception as e:
        return fail(msg=f"打开文件失败: {e}")



@router.delete(
    "/close-file/{file_id}",
    summary="关闭数据库文件",
    response_model=ApiResponse[Empty],
)
async def close_file(file_id: str) -> ApiResponse[Empty]:
    try:
        if file_id in db_services:
            db_services[file_id].close()
            del db_services[file_id]

        async with _current_file_lock:
            global current_file_id
            if current_file_id == file_id:
                current_file_id = None

        file_manager.close_file(file_id)
        return ok(data=Empty(), msg="文件已关闭")
    except Exception as e:
        return fail(msg=f"关闭文件失败: {e}")


@router.delete(
    "/recent-files/{file_id}",
    summary="删除历史记录并关闭后台文件",
    response_model=ApiResponse[Empty],
)
async def delete_recent_file(file_id: str) -> ApiResponse[Empty]:
    try:
        if file_id in db_services:
            db_services[file_id].close()
            del db_services[file_id]

        async with _current_file_lock:
            global current_file_id
            if current_file_id == file_id:
                current_file_id = None

        file_manager.close_file(file_id)

        removed = file_manager.remove_from_history(file_id)
        if not removed:
            return fail(code=1, msg="历史记录不存在")

        return ok(data=Empty(), msg="历史记录已删除")
    except Exception as e:
        return fail(msg=f"删除历史记录失败: {e}")
