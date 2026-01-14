"""
API 路由模块

实现所有 REST API 端点
支持文件管理、数据库操作、表查询等功能
统一返回格式: {code: 状态码, msg: 消息, data: 数据}
"""

import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path
import uuid

from fastapi import APIRouter, HTTPException, Query, Request, UploadFile, File
from pydantic import BaseModel

from ..services.file_manager import file_manager, FileRecord
from ..services.database import DatabaseService


def _safe_filename(name: str) -> str:
    """生成一个尽量安全的文件名（仅用于临时文件保存）。"""
    # 避免路径穿越，保留基础文件名
    base = Path(name).name
    # 极简过滤，去掉不可见字符
    return "".join(ch for ch in base if ch.isprintable()) or "upload.bin"



# 创建路由器
router = APIRouter()

# 全局数据库服务实例字典（按 file_id 存储）
db_services: Dict[str, DatabaseService] = {}

# 全局当前文件 ID（用于兼容性端点）
current_file_id: Optional[str] = None
_current_file_lock = asyncio.Lock()


# Pydantic 模型
class OpenFileRequest(BaseModel):
    """打开文件请求模型"""
    path: str


# 辅助函数
def guess_type(s: str):
    """尝试推断字符串的数据类型"""
    if not s:
        return s

    # 尝试转换为数字
    try:
        return int(s)
    except ValueError:
        pass

    try:
        return float(s)
    except ValueError:
        pass

    # 尝试转换为布尔值
    lower = s.lower()
    if lower in ('true', 'false'):
        return lower == 'true'

    return s


def parse_filter_params(query_params: Dict[str, str]) -> List[Dict[str, Any]]:
    """解析 filter_* 查询参数"""
    filters = []
    supported_ops = {'eq', 'gt', 'gte', 'lt', 'lte', 'contains', 'in'}

    for k, v in query_params.items():
        if not k.startswith('filter_'):
            continue

        # 解析参数名: filter_field 或 filter_field__op
        _, rest = k.split('filter_', 1)
        if '__' in rest:
            field, op = rest.split('__', 1)
        else:
            field, op = rest, 'eq'

        # 验证操作符
        if op not in supported_ops:
            op = 'eq'

        # 解析值
        value = v
        if op == 'in':
            # 处理 in 操作符，按逗号分割
            values = [guess_type(x.strip()) for x in v.split(',') if x.strip()]
            value = values
        else:
            value = guess_type(v)

        filters.append({
            "field": field,
            "op": op,
            "value": value
        })

    return filters


# 统一响应格式
def success_response(data: Any = None, msg: str = "操作成功") -> Dict[str, Any]:
    """成功响应格式"""
    return {"code": 200, "msg": msg, "data": data}


def error_response(code: int = 500, msg: str = "操作失败", data: Any = None) -> Dict[str, Any]:
    """错误响应格式"""
    return {"code": code, "msg": msg, "data": data}


@router.get("/recent-files")
async def get_recent_files():
    """获取最近打开的文件列表"""
    try:
        recent_files = file_manager.get_recent_files(limit=10)
        files_data = []

        for file_record in recent_files:
            files_data.append({
                "file_id": file_record.file_id,
                "path": file_record.path,
                "name": file_record.name,
                "last_opened": file_record.last_opened,
                "file_size": file_record.file_size,
                "engine_name": file_record.engine_name,
            })

        return success_response(data={"files": files_data}, msg="获取最近文件列表成功")

    except Exception as e:
        return error_response(code=500, msg=f"获取最近文件列表失败: {str(e)}")


@router.get("/discover-files")
async def discover_files(directory: Optional[str] = Query(None)):
    """发现指定目录中的 pytuck 文件"""
    try:
        discovered = file_manager.discover_files(directory)
        return success_response(data={"files": discovered}, msg="文件扫描成功")
    except Exception as e:
        return error_response(code=500, msg=f"文件扫描失败: {str(e)}")


@router.post("/upload-open")
async def upload_open(file: UploadFile = File(...)):
    """上传文件并打开（用于拖拽/选择文件场景）。

    说明：浏览器通常无法提供真实本地路径，因此通过上传到后端临时目录后再打开。
    临时文件会记录在 file_manager.temporary_files 中，并在 close/delete 时清理。
    """
    try:
        # 保存到临时目录
        upload_dir = file_manager.config_dir / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)

        suffix = Path(file.filename or "").suffix
        safe_name = _safe_filename(file.filename or "upload")
        tmp_path = upload_dir / f"upload_{Path(safe_name).stem}_{uuid.uuid4().hex}{suffix}"

        with open(tmp_path, "wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)

        # 打开临时文件
        file_record = file_manager.open_file(str(tmp_path))
        if not file_record:
            try:
                tmp_path.unlink()
            except Exception:
                pass
            return error_response(code=404, msg="无法打开文件")

        # 标记为临时文件，便于关闭时清理
        file_manager.temporary_files[file_record.file_id] = str(tmp_path)

        db_service = DatabaseService()
        success = db_service.open_database(str(tmp_path))
        if not success:
            file_manager.close_file(file_record.file_id)
            return error_response(code=500, msg="数据库打开失败")

        db_services[file_record.file_id] = db_service

        try:
            tables = db_service.list_tables()
            real_tables = [t for t in tables if not t.startswith(('⚠️', '💡', '📋'))]
            tables_count = len(real_tables)
        except:
            tables_count = 0

        data = {
            "file_id": file_record.file_id,
            "name": file_record.name,
            "path": file_record.path,
            "tables_count": tables_count,
            "file_size": file_record.file_size,
            "engine_name": file_record.engine_name,
        }

        return success_response(data=data, msg="数据库打开成功")

    except ValueError as e:
        return error_response(code=400, msg=str(e))
    except Exception as e:
        return error_response(code=500, msg=f"上传打开失败: {str(e)}")


@router.post("/open-file")
async def open_file(request: OpenFileRequest):
    """打开数据库文件"""
    try:
        # 使用文件管理器打开文件
        file_record = file_manager.open_file(request.path)
        if not file_record:
            return error_response(code=404, msg="无法打开文件")

        # 创建数据库服务实例
        db_service = DatabaseService()
        success = db_service.open_database(request.path)

        if not success:
            return error_response(code=500, msg="数据库打开失败")

        # 保存数据库服务实例
        db_services[file_record.file_id] = db_service

        # 获取表数量信息
        try:
            tables = db_service.list_tables()
            # 过滤掉占位符表名
            real_tables = [t for t in tables if not t.startswith(('⚠️', '💡', '📋'))]
            tables_count = len(real_tables)
        except:
            tables_count = 0

        data = {
            "file_id": file_record.file_id,
            "name": file_record.name,
            "path": file_record.path,
            "tables_count": tables_count,
            "file_size": file_record.file_size,
            "engine_name": file_record.engine_name,
        }

        return success_response(data=data, msg="数据库打开成功")

    except FileNotFoundError as e:
        return error_response(code=404, msg=str(e))
    except ValueError as e:
        return error_response(code=400, msg=str(e))
    except Exception as e:
        return error_response(code=500, msg=f"打开文件失败: {str(e)}")


@router.delete("/recent-files/{file_id}")
async def delete_recent_file(file_id: str):
    """删除历史记录，并关闭后端已打开的文件（如存在）。"""
    try:
        # 关闭数据库服务
        if file_id in db_services:
            db_services[file_id].close()
            del db_services[file_id]

        # 清理全局 current_file_id
        async with _current_file_lock:
            global current_file_id
            if current_file_id == file_id:
                current_file_id = None

        # 关闭文件（同时会清理 upload-open 临时文件）
        file_manager.close_file(file_id)

        # 从历史记录中移除
        removed = file_manager.remove_from_history(file_id)
        if not removed:
            return error_response(code=404, msg="历史记录不存在")

        return success_response(msg="历史记录已删除")

    except Exception as e:
        return error_response(code=500, msg=f"删除历史记录失败: {str(e)}")


@router.get("/tables/{file_id}")
async def get_tables(file_id: str):
    """获取指定数据库中的表列表"""
    if file_id not in db_services:
        return error_response(code=404, msg="数据库文件未打开")

    try:
        db_service = db_services[file_id]
        tables = db_service.list_tables()

        # 检查是否有占位符表
        placeholder_tables = [t for t in tables if t.startswith(('⚠️', '💡', '📋'))]
        if placeholder_tables:
            return success_response(
                data={"tables": tables, "has_placeholder": True},
                msg="表列表获取成功，但部分功能需要 pytuck 库支持"
            )
        else:
            return success_response(data={"tables": tables, "has_placeholder": False}, msg="表列表获取成功")

    except Exception as e:
        return error_response(code=500, msg=f"获取表列表失败: {str(e)}")


@router.get("/schema/{file_id}/{table_name}")
async def get_table_schema(file_id: str, table_name: str):
    """获取表结构信息"""
    if file_id not in db_services:
        return error_response(code=404, msg="数据库文件未打开")

    try:
        db_service = db_services[file_id]
        table_info = db_service.get_table_info(table_name)

        if not table_info:
            return error_response(code=404, msg=f"表 '{table_name}' 不存在")

        data = {
            "table_name": table_info.name,
            "row_count": table_info.row_count,
            "columns": table_info.columns
        }

        # 检查是否有占位符列
        placeholder_columns = [c for c in table_info.columns if c.get("name", "").startswith('⚠️')]
        if placeholder_columns:
            return success_response(
                data=data,
                msg="表结构获取成功，但列信息功能需要 pytuck 库完善"
            )
        else:
            return success_response(data=data, msg="表结构获取成功")

    except Exception as e:
        return error_response(code=500, msg=f"获取表结构失败: {str(e)}")


@router.get("/rows/{file_id}/{table_name}")
async def get_table_rows(
    file_id: str,
    table_name: str,
    request: Request,
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    limit: int = Query(50, ge=1, le=1000, description="每页行数，最大 1000"),
    sort: Optional[str] = Query(None, description="排序字段"),
    order: str = Query("asc", pattern="^(asc|desc)$", description="排序方向")
):
    """获取表数据（分页，支持过滤）"""
    if file_id not in db_services:
        return error_response(code=404, msg="数据库文件未打开")

    try:
        # 解析过滤参数
        filters = parse_filter_params(dict(request.query_params))

        db_service = db_services[file_id]
        data = db_service.get_table_data(
            table_name=table_name,
            page=page,
            limit=limit,
            sort_by=sort,
            order=order,
            filters=filters
        )

        # 检查是否是占位符数据
        is_placeholder = (
            data.get("rows") and len(data["rows"]) > 0 and
            isinstance(data["rows"][0], dict) and
            data["rows"][0].get("is_placeholder", False)
        )

        if is_placeholder:
            return success_response(
                data=data,
                msg="数据查询功能暂不可用，需要 pytuck 库支持"
            )
        else:
            msg = "表数据获取成功"
            if data.get("server_side"):
                msg += "（使用服务端分页）"
            else:
                msg += "（使用内存分页）"

            if filters:
                msg += f"，应用了 {len(filters)} 个过滤条件"

            return success_response(data=data, msg=msg)

    except Exception as e:
        return error_response(code=500, msg=f"获取表数据失败: {str(e)}")


@router.delete("/close-file/{file_id}")
async def close_file(file_id: str):
    """关闭数据库文件"""
    try:
        # 关闭数据库服务
        if file_id in db_services:
            db_services[file_id].close()
            del db_services[file_id]

        # 清理全局 current_file_id
        async with _current_file_lock:
            global current_file_id
            if current_file_id == file_id:
                current_file_id = None

        # 从文件管理器中移除
        file_manager.close_file(file_id)

        return success_response(msg="文件已关闭")

    except Exception as e:
        return error_response(code=500, msg=f"关闭文件失败: {str(e)}")


@router.post("/use-file/{file_id}")
async def use_file(file_id: str):
    """设置当前操作的数据库文件（用于兼容性端点）"""
    if file_id not in db_services:
        return error_response(code=404, msg="数据库文件未打开")

    async with _current_file_lock:
        global current_file_id
        current_file_id = file_id

    return success_response(
        data={"file_id": file_id},
        msg="设置当前数据库成功"
    )


@router.get("/database-info/{file_id}")
async def get_database_info(file_id: str):
    """获取数据库基本信息"""
    if file_id not in db_services:
        return error_response(code=404, msg="数据库文件未打开")

    try:
        db_service = db_services[file_id]
        info = db_service.get_database_info()

        if "error" in info:
            return error_response(code=500, msg=info["error"])

        return success_response(data=info, msg="数据库信息获取成功")

    except Exception as e:
        return error_response(code=500, msg=f"获取数据库信息失败: {str(e)}")


@router.get("/status")
async def get_status():
    """获取服务状态"""
    data = {
        "service": "pytuck-view",
        "version": "25.1.0",
        "open_databases": len(db_services),
        "status": "running"
    }
    return success_response(data=data, msg="服务状态正常")


# ====================== 集成文档兼容性端点 ======================

@router.post("/database/open")
async def database_open(request: OpenFileRequest):
    """打开数据库文件（集成文档兼容接口）"""
    try:
        # 使用现有的 open_file 逻辑
        file_record = file_manager.open_file(request.path)
        if not file_record:
            raise HTTPException(status_code=404, detail="无法打开文件")

        # 创建数据库服务实例
        db_service = DatabaseService()
        success = db_service.open_database(request.path)

        if not success:
            raise HTTPException(status_code=500, detail="数据库打开失败")

        # 保存数据库服务实例
        db_services[file_record.file_id] = db_service

        # 设置为当前数据库
        async with _current_file_lock:
            global current_file_id
            current_file_id = file_record.file_id

        # 获取表数量信息
        try:
            tables = db_service.list_tables()
            real_tables = [t for t in tables if not t.startswith(('⚠️', '💡', '📋'))]
            tables_count = len(real_tables)
        except:
            tables_count = 0

        # 返回集成文档期望格式
        return {
            "file_id": file_record.file_id,
            "name": file_record.name,
            "path": file_record.path,
            "tables_count": tables_count,
            "file_size": file_record.file_size,
            "engine_name": file_record.engine_name,
            "status": "connected"
        }

    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"打开文件失败: {str(e)}")


async def get_current_file_id() -> str:
    """获取当前文件 ID，如果未设置则尝试推断"""
    async with _current_file_lock:
        fid = current_file_id

    if not fid:
        if len(db_services) == 1:
            # 只有一个打开的数据库，使用它
            fid = next(iter(db_services.keys()))
        else:
            # 多个或无打开的数据库
            if len(db_services) == 0:
                raise HTTPException(status_code=400, detail="没有打开的数据库文件，请先调用 /api/database/open")
            else:
                raise HTTPException(status_code=400, detail="存在多个打开数据库，请调用 /api/use-file/{file_id} 设置当前数据库")

    if fid not in db_services:
        raise HTTPException(status_code=404, detail="当前数据库文件未找到")

    return fid


@router.get("/tables")
async def get_tables_compat():
    """获取当前数据库的表列表（兼容性端点）"""
    try:
        file_id = await get_current_file_id()
        db_service = db_services[file_id]
        tables = db_service.list_tables()

        # 过滤掉占位符表
        real_tables = [t for t in tables if not t.startswith(('⚠️', '💡', '📋'))]

        # 返回集成文档格式
        return {
            "tables": real_tables,
            "total_count": len(real_tables)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取表列表失败: {str(e)}")


@router.get("/tables/{table_name}/schema")
async def get_table_schema_compat(table_name: str):
    """获取表结构（兼容性端点）"""
    try:
        file_id = await get_current_file_id()
        db_service = db_services[file_id]
        table_info = db_service.get_table_info(table_name)

        if not table_info:
            raise HTTPException(status_code=404, detail=f"表 '{table_name}' 不存在")

        # 返回集成文档格式
        return {
            "name": table_info.name,
            "comment": "",  # pytuck 中暂无注释支持
            "primary_key": None,  # 可以从 columns 中推断
            "record_count": table_info.row_count,
            "columns": table_info.columns
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取表结构失败: {str(e)}")


@router.get("/tables/{table_name}/data")
async def get_table_data_compat(
    table_name: str,
    request: Request,
    limit: int = Query(50, ge=1, le=1000, description="每页行数"),
    offset: int = Query(0, ge=0, description="偏移量"),
    order_by: Optional[str] = Query(None, description="排序字段"),
    order_desc: bool = Query(False, description="是否降序")
):
    """获取表数据（兼容性端点）"""
    try:
        file_id = await get_current_file_id()
        db_service = db_services[file_id]

        # 解析过滤参数
        filters = parse_filter_params(dict(request.query_params))

        # 计算页码
        page = (offset // limit) + 1

        # 调用数据库服务
        data = db_service.get_table_data(
            table_name=table_name,
            page=page,
            limit=limit,
            sort_by=order_by,
            order=("desc" if order_desc else "asc"),
            filters=filters
        )

        # 获取表结构用于返回 schema
        table_info = db_service.get_table_info(table_name)
        schema = table_info.columns if table_info else []

        # 返回集成文档格式
        total_pages = (data["total"] + limit - 1) // limit
        current_page = page

        return {
            "data": data["rows"],
            "pagination": {
                "page": current_page,
                "per_page": limit,
                "total_records": data["total"],
                "total_pages": total_pages,
                "has_next": current_page < total_pages,
                "has_prev": current_page > 1
            },
            "schema": schema
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取表数据失败: {str(e)}")