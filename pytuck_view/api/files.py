"""文件相关 API 路由

包含：
- 最近文件
- 发现文件
- 打开文件（本地路径）
- 关闭文件 / 删除历史
- 翻译文件

统一前缀由 app.include_router(..., prefix="/api") 提供。
"""

import asyncio
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from pytuck_view.base.constants import HOME_DIR
from pytuck_view.base.exceptions import ResultWarningException, ServiceException
from pytuck_view.base.i18n import ApiSummaryI18n, ConvertI18n, FileI18n
from pytuck_view.base.response import ResponseUtil
from pytuck_view.base.schemas import ApiResponse, Empty, SuccessResult
from pytuck_view.services.database import DatabaseService
from pytuck_view.services.file_manager import file_manager

router = APIRouter()

# 全局数据库服务实例字典（按 file_id 存储）
db_services: dict[str, DatabaseService] = {}

# 全局当前文件 ID（兼容性逻辑已废弃，但当前仍用于内部管理）
current_file_id: str | None = None
_current_file_lock = asyncio.Lock()


@router.get(
    "/recent-files",
    summary="获取最近打开的文件列表",
    response_model=ApiResponse[dict[str, Any]],
)
@ResponseUtil(i18n_summary=ApiSummaryI18n.GET_RECENT_FILES)
async def get_recent_files() -> dict[str, Any]:
    """获取最近打开的文件列表"""
    recent_files = file_manager.get_recent_files(limit=10)
    files_data = [f.model_dump() for f in recent_files]
    return {"files": files_data}


@router.get(
    "/discover-files",
    summary="发现指定目录中的 pytuck 文件",
    response_model=ApiResponse[dict[str, Any]],
)
@ResponseUtil(i18n_summary=ApiSummaryI18n.DISCOVER_FILES)
async def discover_files(
    directory: str | None = Query(None),
) -> SuccessResult[dict[str, Any]]:
    """发现指定目录中的 pytuck 文件"""
    discovered = file_manager.discover_files(directory)
    return SuccessResult(data={"files": discovered}, i18n_msg=None)


class OpenFileBody(BaseModel):
    path: str


@router.post(
    "/open-file",
    summary="打开数据库文件",
    response_model=ApiResponse[dict[str, Any]],
)
@ResponseUtil(i18n_summary=ApiSummaryI18n.OPEN_FILE)
async def open_file(request: OpenFileBody) -> SuccessResult[dict[str, Any]]:
    """打开数据库文件"""
    file_record = file_manager.open_file(request.path)
    if not file_record:
        raise ServiceException(FileI18n.CANNOT_OPEN_FILE)

    db_service = DatabaseService()
    success = db_service.open_database(request.path)
    if not success:
        raise ServiceException(FileI18n.DATABASE_OPEN_FAILED)

    db_services[file_record.file_id] = db_service

    # 获取表数量
    tables = db_service.list_tables()
    tables_count = len(tables)

    data: dict[str, Any] = {
        "file_id": file_record.file_id,
        "name": file_record.name,
        "path": file_record.path,
        "file_size": file_record.file_size,
        "engine_name": file_record.engine_name,
        "tables_count": tables_count,
    }
    return SuccessResult(data=data, i18n_msg=FileI18n.OPEN_FILE_SUCCESS)


@router.delete(
    "/close-file/{file_id}",
    summary="关闭数据库文件",
    response_model=ApiResponse[Empty],
)
@ResponseUtil(i18n_summary=ApiSummaryI18n.CLOSE_FILE)
async def close_file(file_id: str) -> SuccessResult[Empty]:
    """关闭数据库文件"""
    if file_id in db_services:
        db_services[file_id].close()
        del db_services[file_id]

    async with _current_file_lock:
        global current_file_id
        if current_file_id == file_id:
            current_file_id = None

    file_manager.close_file(file_id)
    return SuccessResult(data=Empty(), i18n_msg=FileI18n.CLOSE_FILE_SUCCESS)


@router.delete(
    "/recent-files/{file_id}",
    summary="删除历史记录并关闭后台文件",
    response_model=ApiResponse[Empty],
)
@ResponseUtil(i18n_summary=ApiSummaryI18n.DELETE_RECENT_FILE)
async def delete_recent_file(file_id: str) -> SuccessResult[Empty]:
    """删除历史记录并关闭后台文件"""
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
        raise ResultWarningException(FileI18n.HISTORY_NOT_EXISTS)

    return SuccessResult(data=Empty(), i18n_msg=FileI18n.DELETE_RECENT_FILE_SUCCESS)


@router.get(
    "/user-home",
    summary="获取用户主目录",
    response_model=ApiResponse[dict[str, Any]],
)
@ResponseUtil(i18n_summary=ApiSummaryI18n.GET_USER_HOME)
async def get_user_home() -> SuccessResult[dict[str, Any]]:
    """获取用户主目录路径"""
    home = str(Path.home())
    return SuccessResult(data={"home": home}, i18n_msg=None)


@router.get(
    "/last-browse-directory",
    summary="获取最后浏览的目录",
    response_model=ApiResponse[dict[str, Any]],
)
@ResponseUtil(i18n_summary=ApiSummaryI18n.GET_LAST_BROWSE_DIRECTORY)
async def get_last_browse_directory() -> SuccessResult[dict[str, Any]]:
    """获取最后浏览的目录，为空则返回当前工作目录"""
    last_dir = file_manager.get_last_browse_directory()
    if not last_dir or not Path(last_dir).exists():
        # 使用当前工作目录作为默认
        last_dir = str(Path.cwd())

    return SuccessResult(data={"directory": last_dir}, i18n_msg=None)


@router.get(
    "/browse-directory",
    summary="浏览目录内容",
    response_model=ApiResponse[dict[str, Any]],
)
@ResponseUtil(i18n_summary=ApiSummaryI18n.BROWSE_DIRECTORY)
async def browse_directory(
    path: str | None = Query(None),
) -> SuccessResult[dict[str, Any]]:
    """浏览指定目录的文件和子目录

    Args:
        path: 目录路径，为空时使用用户主目录

    Returns:
        包含目录路径和条目列表的响应
    """
    # 确定目标目录
    if path:
        target = Path(path).expanduser().resolve(strict=False)
    else:
        target = Path.home()

    # 检查路径有效性
    if not target.exists():
        raise ServiceException(FileI18n.PATH_NOT_EXISTS)
    if not target.is_dir():
        raise ServiceException(FileI18n.NOT_A_DIRECTORY)

    # 不再筛选文件后缀，显示所有文件
    entries = []

    try:
        # 遍历目录内容
        for child in sorted(
            target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())
        ):
            try:
                if child.is_dir():
                    # 添加子目录
                    entries.append(
                        {
                            "name": child.name,
                            "path": str(child.resolve()),
                            "type": "dir",
                            "size": None,
                            "mtime": child.stat().st_mtime,
                        }
                    )
                elif child.is_file():
                    # 添加所有文件（不做后缀筛选）
                    entries.append(
                        {
                            "name": child.name,
                            "path": str(child.resolve()),
                            "type": "file",
                            "size": child.stat().st_size,
                            "mtime": child.stat().st_mtime,
                        }
                    )
            except PermissionError:
                # 跳过无权限的条目
                continue
    except PermissionError:
        raise ServiceException(FileI18n.ACCESS_DENIED)

    # 在成功返回前，记录这次浏览的目录
    try:
        file_manager.update_last_browse_directory(str(target))
    except Exception:
        pass  # 记录失败不影响响应

    return SuccessResult(data={"path": str(target), "entries": entries}, i18n_msg=None)


# ========== 翻译文件 ==========


@router.get(
    "/locales/{locale}",
    summary="获取前端翻译文件",
)
async def get_locale(locale: str) -> dict[str, str]:
    """获取指定语言的翻译 JSON（不走 ResponseUtil，直接返回纯翻译对象）"""
    # 安全校验：仅允许已知 locale，防止路径穿越
    allowed = {"zh_cn", "en_us"}
    if locale not in allowed:
        raise HTTPException(status_code=404, detail="Locale not found")
    locale_file = HOME_DIR / "locales" / f"{locale}.json"
    if not locale_file.exists():
        raise HTTPException(status_code=404, detail="Locale not found")
    with open(locale_file, encoding="utf-8") as f:
        result: dict[str, str] = json.load(f)
    return result


# ========== 文件备注 ==========


class UpdateNoteBody(BaseModel):
    """更新文件备注请求体"""

    note: str


@router.patch(
    "/recent-files/{file_id}/note",
    summary="更新文件备注",
    response_model=ApiResponse[Empty],
)
@ResponseUtil(i18n_summary=ApiSummaryI18n.UPDATE_FILE_NOTE)
async def update_file_note(
    file_id: str, body: UpdateNoteBody
) -> SuccessResult[Empty]:
    """更新最近文件的备注信息"""
    success = file_manager.update_note(file_id, body.note)
    if not success:
        raise ResultWarningException(FileI18n.HISTORY_NOT_EXISTS)
    return SuccessResult(data=Empty(), i18n_msg=FileI18n.UPDATE_NOTE_SUCCESS)


# ========== 引擎转换 ==========


@router.get(
    "/available-engines",
    summary="获取可用引擎列表",
    response_model=ApiResponse[dict[str, Any]],
)
@ResponseUtil(i18n_summary=ApiSummaryI18n.GET_AVAILABLE_ENGINES)
async def available_engines() -> SuccessResult[dict[str, Any]]:
    """获取 pytuck 支持的所有引擎及其可用状态"""
    from pytuck.tools import get_available_engines

    engines = get_available_engines()
    return SuccessResult(data={"engines": engines}, i18n_msg=None)


class ConvertEngineBody(BaseModel):
    """引擎转换请求体"""

    source_path: str
    source_engine: str
    target_engine: str
    target_path: str


@router.post(
    "/convert-engine",
    summary="引擎转换",
    response_model=ApiResponse[dict[str, Any]],
)
@ResponseUtil(i18n_summary=ApiSummaryI18n.CONVERT_ENGINE)
async def convert_engine(body: ConvertEngineBody) -> SuccessResult[dict[str, Any]]:
    """将数据库文件从一种引擎格式转换为另一种"""
    from pytuck.tools import migrate_engine

    source = Path(body.source_path)
    target = Path(body.target_path)

    if not source.exists():
        raise ServiceException(FileI18n.FILE_NOT_FOUND, path=body.source_path)
    if target.exists():
        raise ServiceException(ConvertI18n.TARGET_FILE_EXISTS, path=body.target_path)

    try:
        result = migrate_engine(
            source_path=source,
            source_engine=body.source_engine,
            target_path=target,
            target_engine=body.target_engine,
        )
    except Exception as e:
        raise ServiceException(ConvertI18n.CONVERT_FAILED, detail=str(e)) from e

    # 将新文件加入最近文件列表
    file_record = file_manager.add_file_to_history(str(target))

    return SuccessResult(
        data={
            "tables": result.get("tables", 0),
            "records": result.get("records", 0),
            "target_path": str(target),
            "engine_name": file_record.engine_name,
        },
        i18n_msg=ConvertI18n.CONVERT_SUCCESS,
    )
