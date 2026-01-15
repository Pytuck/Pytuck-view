"""表/数据相关 API 路由"""

from typing import Any
from fastapi import APIRouter, Query, Request

from .files import db_services
from .schemas import ApiResponse, PageData, fail, ok

router = APIRouter()


@router.get(
    "/tables/{file_id}",
    summary="获取指定数据库的表列表",
    response_model=ApiResponse[dict],
)
async def get_tables(file_id: str) -> ApiResponse[dict]:
    if file_id not in db_services:
        return fail(code=1, msg="数据库文件未打开")

    try:
        db_service = db_services[file_id]
        tables = db_service.list_tables()

        placeholder_tables = [t for t in tables if t.startswith(("⚠️", "💡", "📋"))]
        if placeholder_tables:
            return ok(
                data={"tables": tables, "has_placeholder": True},
                msg="表列表获取成功，但部分功能需要 pytuck 库支持",
            )

        return ok(data={"tables": tables, "has_placeholder": False}, msg="表列表获取成功")
    except Exception as e:
        return fail(msg=f"获取表列表失败: {e}")


@router.get(
    "/schema/{file_id}/{table_name}",
    summary="获取表结构信息",
    response_model=ApiResponse[dict],
)
async def get_table_schema(file_id: str, table_name: str) -> ApiResponse[dict]:
    if file_id not in db_services:
        return fail(code=1, msg="数据库文件未打开")

    try:
        db_service = db_services[file_id]
        table_info = db_service.get_table_info(table_name)

        if not table_info:
            return fail(code=1, msg=f"表 '{table_name}' 不存在")

        data = {
            "table_name": table_info.name,
            "row_count": table_info.row_count,
            "columns": table_info.columns,
        }

        placeholder_columns = [
            c for c in table_info.columns if c.get("name", "").startswith("⚠️")
        ]
        if placeholder_columns:
            return ok(data=data, msg="表结构获取成功，但列信息功能需要 pytuck 库完善")

        return ok(data=data, msg="表结构获取成功")
    except Exception as e:
        return fail(msg=f"获取表结构失败: {e}")


@router.get(
    "/rows/{file_id}/{table_name}",
    summary="获取表数据（分页，支持过滤）",
    response_model=ApiResponse[PageData],
)
async def get_table_rows(
    file_id: str,
    table_name: str,
    request: Request,
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    limit: int = Query(50, ge=1, le=1000, description="每页行数，最大 1000"),
    sort: str | None = Query(None, description="排序字段"),
    order: str = Query("asc", pattern="^(asc|desc)$", description="排序方向"),
) -> ApiResponse[PageData]:
    if file_id not in db_services:
        return fail(code=1, msg="数据库文件未打开")

    try:
        filters = _parse_filter_params(dict(request.query_params))
        db_service = db_services[file_id]
        raw = db_service.get_table_data(
            table_name=table_name,
            page=page,
            limit=limit,
            sort_by=sort,
            order=order,
            filters=filters,
        )

        payload = PageData(
            page=int(raw.get("page", page)),
            limit=int(raw.get("limit", limit)),
            total=int(raw.get("total", 0)),
            rows=list(raw.get("rows", [])),
        )

        msg = "表数据获取成功"
        if raw.get("server_side"):
            msg += "（使用服务端分页）"
        else:
            msg += "（使用内存分页）"
        if filters:
            msg += f"，应用了 {len(filters)} 个过滤条件"

        is_placeholder = (
            payload.rows
            and isinstance(payload.rows[0], dict)
            and payload.rows[0].get("is_placeholder", False)
        )
        if is_placeholder:
            return ok(data=payload, msg="数据查询功能暂不可用，需要 pytuck 库支持")

        return ok(data=payload, msg=msg)
    except Exception as e:
        return fail(msg=f"获取表数据失败: {e}")


def _guess_type(s: str) -> Any:
    """猜测类型"""
    if not s:
        return s
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    lower = s.lower()
    if lower in ("true", "false"):
        return lower == "true"
    return s


def _parse_filter_params(query_params: dict[str, str]) -> list[dict[str, Any]]:
    filters: list[dict[str, Any]] = []
    supported_ops = {"eq", "gt", "gte", "lt", "lte", "contains", "in"}

    for k, v in query_params.items():
        if not k.startswith("filter_"):
            continue

        _, rest = k.split("filter_", 1)
        if "__" in rest:
            field, op = rest.split("__", 1)
        else:
            field, op = rest, "eq"

        if op not in supported_ops:
            op = "eq"

        if op == "in":
            value: Any = [_guess_type(x.strip()) for x in v.split(",") if x.strip()]
        else:
            value = _guess_type(v)

        filters.append({"field": field, "op": op, "value": value})

    return filters
