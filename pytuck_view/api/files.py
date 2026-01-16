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
from ..base.schemas import ApiResponse, Empty, fail, ok

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

        # 获取表数量
        tables = db_service.list_tables()
        tables_count = len(tables)

        data = {
            "file_id": file_record.file_id,
            "name": file_record.name,
            "path": file_record.path,
            "file_size": file_record.file_size,
            "engine_name": file_record.engine_name,
            "tables_count": tables_count,
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


@router.get(
    "/user-home",
    summary="获取用户主目录",
    response_model=ApiResponse[dict],
)
async def get_user_home() -> ApiResponse[dict]:
    """获取用户主目录路径"""
    try:
        home = str(Path.home())
        return ok(data={"home": home}, msg="获取用户主目录成功")
    except Exception as e:
        return fail(msg=f"无法获取用户主目录: {e}")


@router.get(
    "/last-browse-directory",
    summary="获取最后浏览的目录",
    response_model=ApiResponse[dict],
)
async def get_last_browse_directory() -> ApiResponse[dict]:
    """获取最后浏览的目录，为空则返回当前工作目录"""
    try:
        last_dir = file_manager.get_last_browse_directory()
        if not last_dir or not Path(last_dir).exists():
            # 使用当前工作目录作为默认
            last_dir = str(Path.cwd())

        return ok(data={"directory": last_dir}, msg="获取最后浏览目录成功")
    except Exception as e:
        return fail(msg=f"获取最后浏览目录失败: {e}")


@router.get(
    "/browse-directory",
    summary="浏览目录内容",
    response_model=ApiResponse[dict],
)
async def browse_directory(path: str | None = Query(None)) -> ApiResponse[dict]:
    """浏览指定目录的文件和子目录

    Args:
        path: 目录路径，为空时使用用户主目录

    Returns:
        包含目录路径和条目列表的响应
    """
    try:
        # 确定目标目录
        if path:
            target = Path(path).expanduser().resolve(strict=False)
        else:
            target = Path.home()

        # 检查路径有效性
        if not target.exists():
            return fail(code=1, msg="路径不存在")
        if not target.is_dir():
            return fail(code=1, msg="不是目录")

        # 不再筛选文件后缀，显示所有文件
        entries = []

        try:
            # 遍历目录内容
            for child in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                try:
                    if child.is_dir():
                        # 添加子目录
                        entries.append({
                            "name": child.name,
                            "path": str(child.resolve()),
                            "type": "dir",
                            "size": None,
                            "mtime": child.stat().st_mtime,
                        })
                    elif child.is_file():
                        # 添加所有文件（不做后缀筛选）
                        entries.append({
                            "name": child.name,
                            "path": str(child.resolve()),
                            "type": "file",
                            "size": child.stat().st_size,
                            "mtime": child.stat().st_mtime,
                        })
                except PermissionError:
                    # 跳过无权限的条目
                    continue
        except PermissionError:
            return fail(code=1, msg="无法访问该目录（权限不足）")

        # 在成功返回前，记录这次浏览的目录
        try:
            file_manager.update_last_browse_directory(str(target))
        except Exception:
            pass  # 记录失败不影响响应

        return ok(
            data={"path": str(target), "entries": entries},
            msg="浏览目录成功",
        )
    except Exception as e:
        return fail(msg=f"浏览目录失败: {e}")
