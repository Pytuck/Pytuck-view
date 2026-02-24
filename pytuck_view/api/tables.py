"""表/数据相关 API 路由"""

from typing import Any

from fastapi import APIRouter, Query, Request

from pytuck_view.api.files import db_services
from pytuck_view.base.exceptions import ServiceException
from pytuck_view.base.i18n import ApiSummaryI18n, DatabaseI18n
from pytuck_view.base.response import ResponseUtil
from pytuck_view.base.schemas import (
    ApiResponse,
    ColumnSchema,
    DeleteRowData,
    DeleteRowRequest,
    DropTableData,
    FilterItem,
    GetTableSchemaData,
    GetTablesData,
    InsertRowData,
    InsertRowRequest,
    PageData,
    RenameTableData,
    RenameTableRequest,
    SuccessResult,
    TableMetadataItem,
    TablePrimaryKeyData,
    UpdateColumnCommentData,
    UpdateCommentRequest,
    UpdateRowData,
    UpdateRowRequest,
    UpdateTableCommentData,
)

router = APIRouter()


@router.get(
    "/tables/{file_id}",
    summary="获取指定数据库的表列表",
    response_model=ApiResponse[GetTablesData],
)
@ResponseUtil(i18n_summary=ApiSummaryI18n.GET_TABLES)
async def get_tables(file_id: str) -> SuccessResult[GetTablesData]:
    """获取指定数据库的表列表(包含备注信息)"""
    if file_id not in db_services:
        raise ServiceException(DatabaseI18n.DB_NOT_OPENED)

    db_service = db_services[file_id]
    table_names = db_service.list_tables()

    # 获取每个表的元数据(名称和备注)
    tables_with_metadata: list[TableMetadataItem] = []
    for table_name in table_names:
        table_info = db_service.get_table_info(table_name)
        tables_with_metadata.append(
            TableMetadataItem(
                name=table_name,
                comment=table_info.comment if table_info else None,
            )
        )

    placeholder_tables = [t for t in table_names if t.startswith(("⚠️", "💡", "📋"))]
    if placeholder_tables:
        return SuccessResult(
            data=GetTablesData(tables=tables_with_metadata, has_placeholder=True),
            i18n_msg=DatabaseI18n.GET_TABLES_WITH_PLACEHOLDER,
        )

    return SuccessResult(
        data=GetTablesData(tables=tables_with_metadata, has_placeholder=False),
        i18n_msg=None,
    )


@router.get(
    "/schema/{file_id}/{table_name}",
    summary="获取表结构信息",
    response_model=ApiResponse[GetTableSchemaData],
)
@ResponseUtil(i18n_summary=ApiSummaryI18n.GET_TABLE_SCHEMA)
async def get_table_schema(
    file_id: str, table_name: str
) -> SuccessResult[GetTableSchemaData]:
    """获取表结构信息"""
    if file_id not in db_services:
        raise ServiceException(DatabaseI18n.DB_NOT_OPENED)

    db_service = db_services[file_id]
    table_info = db_service.get_table_info(table_name)

    if not table_info:
        raise ServiceException(DatabaseI18n.TABLE_NOT_EXISTS, table_name=table_name)

    columns = [ColumnSchema(**col) for col in table_info.columns]
    data = GetTableSchemaData(
        table_name=table_info.name,
        row_count=table_info.row_count,
        columns=columns,
        table_comment=table_info.comment,
    )

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
    # services 层接受 list[dict]，需要转换
    filters_as_dicts = [f.model_dump() for f in filters]
    raw = db_service.get_table_data(
        table_name=table_name,
        page=page,
        limit=limit,
        sort_by=sort,
        order=order,
        filters=filters_as_dicts,
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


def _guess_type(s: str) -> int | float | bool | str:
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


def _parse_filter_params(query_params: dict[str, str]) -> list[FilterItem]:
    """解析查询参数中的过滤条件"""
    filters: list[FilterItem] = []
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
            value: int | float | bool | str | list[int | float | bool | str] = [
                _guess_type(x.strip()) for x in v.split(",") if x.strip()
            ]
        else:
            value = _guess_type(v)

        filters.append(FilterItem(field=field, op=op, value=value))

    return filters


# ========== Schema 修改接口 ==========


@router.post(
    "/tables/{file_id}/{table_name}/rename",
    summary="重命名表",
    response_model=ApiResponse[RenameTableData],
)
@ResponseUtil(i18n_summary=ApiSummaryI18n.RENAME_TABLE)
async def rename_table(
    file_id: str, table_name: str, body: RenameTableRequest
) -> SuccessResult[RenameTableData]:
    """重命名表"""
    if file_id not in db_services:
        raise ServiceException(DatabaseI18n.DB_NOT_OPENED)

    db_service = db_services[file_id]
    db_service.rename_table(table_name, body.new_name)

    return SuccessResult(
        data=RenameTableData(old_name=table_name, new_name=body.new_name),
        i18n_msg=DatabaseI18n.RENAME_TABLE_SUCCESS,
    )


@router.post(
    "/tables/{file_id}/{table_name}/comment",
    summary="更新表备注",
    response_model=ApiResponse[UpdateTableCommentData],
)
@ResponseUtil(i18n_summary=ApiSummaryI18n.UPDATE_TABLE_COMMENT)
async def update_table_comment(
    file_id: str, table_name: str, body: UpdateCommentRequest
) -> SuccessResult[UpdateTableCommentData]:
    """更新表备注"""
    if file_id not in db_services:
        raise ServiceException(DatabaseI18n.DB_NOT_OPENED)

    db_service = db_services[file_id]
    db_service.update_table_comment(table_name, body.comment)

    return SuccessResult(
        data=UpdateTableCommentData(table_name=table_name, comment=body.comment),
        i18n_msg=DatabaseI18n.UPDATE_COMMENT_SUCCESS,
    )


@router.post(
    "/columns/{file_id}/{table_name}/{column_name}/comment",
    summary="更新列备注",
    response_model=ApiResponse[UpdateColumnCommentData],
)
@ResponseUtil(i18n_summary=ApiSummaryI18n.UPDATE_COLUMN_COMMENT)
async def update_column_comment(
    file_id: str, table_name: str, column_name: str, body: UpdateCommentRequest
) -> SuccessResult[UpdateColumnCommentData]:
    """更新列备注"""
    if file_id not in db_services:
        raise ServiceException(DatabaseI18n.DB_NOT_OPENED)

    db_service = db_services[file_id]
    db_service.update_column_comment(table_name, column_name, body.comment)

    return SuccessResult(
        data=UpdateColumnCommentData(
            table_name=table_name,
            column_name=column_name,
            comment=body.comment,
        ),
        i18n_msg=DatabaseI18n.UPDATE_COMMENT_SUCCESS,
    )


# ========== 数据行操作接口 ==========


@router.post(
    "/rows/{file_id}/{table_name}",
    summary="插入行",
    response_model=ApiResponse[InsertRowData],
)
@ResponseUtil(i18n_summary=ApiSummaryI18n.INSERT_ROW)
async def insert_row(
    file_id: str, table_name: str, body: InsertRowRequest
) -> SuccessResult[InsertRowData]:
    """插入一行数据"""
    if file_id not in db_services:
        raise ServiceException(DatabaseI18n.DB_NOT_OPENED)

    db_service = db_services[file_id]
    pk = db_service.insert_row(table_name, body.data)

    return SuccessResult(
        data=InsertRowData(inserted_pk=pk),
        i18n_msg=DatabaseI18n.INSERT_ROW_SUCCESS,
    )


@router.put(
    "/rows/{file_id}/{table_name}",
    summary="更新行",
    response_model=ApiResponse[UpdateRowData],
)
@ResponseUtil(i18n_summary=ApiSummaryI18n.UPDATE_ROW)
async def update_row(
    file_id: str, table_name: str, body: UpdateRowRequest
) -> SuccessResult[UpdateRowData]:
    """更新一行数据"""
    if file_id not in db_services:
        raise ServiceException(DatabaseI18n.DB_NOT_OPENED)

    db_service = db_services[file_id]
    db_service.update_row(table_name, body.pk, body.data)

    return SuccessResult(
        data=UpdateRowData(updated=True, pk=body.pk),
        i18n_msg=DatabaseI18n.UPDATE_ROW_SUCCESS,
    )


@router.delete(
    "/rows/{file_id}/{table_name}",
    summary="删除行",
    response_model=ApiResponse[DeleteRowData],
)
@ResponseUtil(i18n_summary=ApiSummaryI18n.DELETE_ROW)
async def delete_row(
    file_id: str, table_name: str, body: DeleteRowRequest
) -> SuccessResult[DeleteRowData]:
    """删除一行数据"""
    if file_id not in db_services:
        raise ServiceException(DatabaseI18n.DB_NOT_OPENED)

    db_service = db_services[file_id]
    db_service.delete_row(table_name, body.pk)

    return SuccessResult(
        data=DeleteRowData(deleted=True, pk=body.pk),
        i18n_msg=DatabaseI18n.DELETE_ROW_SUCCESS,
    )


@router.delete(
    "/tables/{file_id}/{table_name}",
    summary="删除表",
    response_model=ApiResponse[DropTableData],
)
@ResponseUtil(i18n_summary=ApiSummaryI18n.DROP_TABLE)
async def drop_table(file_id: str, table_name: str) -> SuccessResult[DropTableData]:
    """删除整张表（包含所有数据）"""
    if file_id not in db_services:
        raise ServiceException(DatabaseI18n.DB_NOT_OPENED)

    db_service = db_services[file_id]
    db_service.drop_table(table_name)

    return SuccessResult(
        data=DropTableData(deleted=True, table_name=table_name),
        i18n_msg=DatabaseI18n.DROP_TABLE_SUCCESS,
    )


@router.get(
    "/schema/{file_id}/{table_name}/primary-key",
    summary="获取表主键信息",
    response_model=ApiResponse[TablePrimaryKeyData],
)
@ResponseUtil(i18n_summary=ApiSummaryI18n.GET_TABLE_SCHEMA)
async def get_table_primary_key(
    file_id: str, table_name: str
) -> SuccessResult[TablePrimaryKeyData]:
    """获取表的主键列信息"""
    if file_id not in db_services:
        raise ServiceException(DatabaseI18n.DB_NOT_OPENED)

    db_service = db_services[file_id]
    pk_column = db_service.get_primary_key_column(table_name)
    is_user_pk = db_service.has_user_primary_key(table_name)

    return SuccessResult(
        data=TablePrimaryKeyData(
            table_name=table_name,
            primary_key=pk_column,
            has_primary_key=pk_column is not None,
            is_pseudo_pk=not is_user_pk and pk_column is not None,
        ),
        i18n_msg=None,
    )
