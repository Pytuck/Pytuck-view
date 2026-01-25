"""表/数据相关 API 路由"""

from typing import Any

from fastapi import APIRouter, Query, Request

from pytuck_view.api.files import db_services
from pytuck_view.base.exceptions import ServiceException
from pytuck_view.base.i18n import ApiSummaryI18n, DatabaseI18n
from pytuck_view.base.response import ResponseUtil
from pytuck_view.base.schemas import ApiResponse, PageData, SuccessResult

router = APIRouter()


@router.get(
    "/tables/{file_id}",
    summary="获取指定数据库的表列表",
    response_model=ApiResponse[dict[str, Any]],
)
@ResponseUtil(i18n_summary=ApiSummaryI18n.GET_TABLES)
async def get_tables(file_id: str) -> SuccessResult[dict[str, Any]]:
    """获取指定数据库的表列表(包含备注信息)"""
    if file_id not in db_services:
        raise ServiceException(DatabaseI18n.DB_NOT_OPENED)

    db_service = db_services[file_id]
    table_names = db_service.list_tables()

    # 获取每个表的元数据(名称和备注)
    tables_with_metadata: list[dict[str, Any]] = []
    for table_name in table_names:
        table_info = db_service.get_table_info(table_name)
        tables_with_metadata.append({
            "name": table_name,
            "comment": table_info.comment if table_info else None
        })

    placeholder_tables = [t for t in table_names if t.startswith(("⚠️", "💡", "📋"))]
    if placeholder_tables:
        return SuccessResult(
            data={"tables": tables_with_metadata, "has_placeholder": True},
            i18n_msg=DatabaseI18n.GET_TABLES_WITH_PLACEHOLDER,
        )

    return SuccessResult(
        data={"tables": tables_with_metadata, "has_placeholder": False},
        i18n_msg=None,
    )


@router.get(
    "/schema/{file_id}/{table_name}",
    summary="获取表结构信息",
    response_model=ApiResponse[dict[str, Any]],
)
@ResponseUtil(i18n_summary=ApiSummaryI18n.GET_TABLE_SCHEMA)
async def get_table_schema(
    file_id: str, table_name: str
) -> SuccessResult[dict[str, Any]]:
    """获取表结构信息"""
    if file_id not in db_services:
        raise ServiceException(DatabaseI18n.DB_NOT_OPENED)

    db_service = db_services[file_id]
    table_info = db_service.get_table_info(table_name)

    if not table_info:
        raise ServiceException(DatabaseI18n.TABLE_NOT_EXISTS, table_name=table_name)

    data: dict[str, Any] = {
        "table_name": table_info.name,
        "row_count": table_info.row_count,
        "columns": table_info.columns,
        "table_comment": table_info.comment,
    }

    placeholder_columns = [
        c for c in table_info.columns if c.get("name", "").startswith("⚠️")
    ]
    if placeholder_columns:
        return SuccessResult(
            data=data, i18n_msg=DatabaseI18n.GET_SCHEMA_WITH_PLACEHOLDER
        )

    return SuccessResult(data=data, i18n_msg=None)


@router.get(
    "/rows/{file_id}/{table_name}",
    summary="获取表数据（分页，支持过滤）",
    response_model=ApiResponse[PageData[Any]],
)
@ResponseUtil(i18n_summary=ApiSummaryI18n.GET_TABLE_ROWS)
async def get_table_rows(
    file_id: str,
    table_name: str,
    request: Request,
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    limit: int = Query(50, ge=1, le=1000, description="每页行数，最大 1000"),
    sort: str | None = Query(None, description="排序字段"),
    order: str = Query("asc", pattern="^(asc|desc)$", description="排序方向"),
) -> SuccessResult[PageData[Any]]:
    """获取表数据（分页，支持过滤）"""
    if file_id not in db_services:
        raise ServiceException(DatabaseI18n.DB_NOT_OPENED)

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

    payload: PageData[Any] = PageData(
        page=int(raw.get("page", page)),
        limit=int(raw.get("limit", limit)),
        total=int(raw.get("total", 0)),
        rows=list(raw.get("rows", [])),
    )

    # 检查是否为 placeholder 数据
    is_placeholder = (
        payload.rows
        and isinstance(payload.rows[0], dict)
        and payload.rows[0].get("is_placeholder", False)
    )
    if is_placeholder:
        return SuccessResult(data=payload, i18n_msg=DatabaseI18n.GET_ROWS_PLACEHOLDER)

    # 构造分页类型文本
    pagination = "使用服务端分页" if raw.get("server_side") else "使用内存分页"

    # 根据过滤条件返回不同消息
    if filters:
        return SuccessResult(
            data=payload,
            i18n_msg=DatabaseI18n.GET_ROWS_WITH_FILTER,
            i18n_args={"pagination": pagination, "filter_count": len(filters)},
        )

    return SuccessResult(
        data=payload,
        i18n_msg=DatabaseI18n.GET_ROWS_SUCCESS,
        i18n_args={"pagination": pagination},
    )


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
