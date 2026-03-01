"""API Schema 定义

本模块用于：
- 定义统一响应结构 ApiResponse[T]（code/msg/data）
- 定义常用的通用数据模型（分页、列表等）
- 定义 API 请求体模型和响应数据模型

约定：
- `code` 为业务码：0=成功，1=失败，2=警告
- HTTP status 仍按语义返回（由路由决定）
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from pytuck_view.utils.schemas import I18nMessage

# ========== 通用模型 ==========


class FileRecord(BaseModel):
    """文件记录数据类"""

    file_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="文件 ID"
    )
    path: str = Field(..., description="文件路径")
    name: str = Field(..., description="文件名")
    last_opened: str = Field(datetime.now().isoformat(), description="最后打开时间")
    file_size: int = Field(0, description="文件大小")
    engine_name: str = Field(..., description="引擎名称")
    note: str = Field(default="", description="用户备注")


class ApiResponse[T](BaseModel):
    """统一响应模型（泛型）。"""

    code: int = Field(0, description="业务码：0=成功，1=失败，2=警告")
    msg: str = Field("OK", description="提示信息")
    data: T | None = Field(None, description="响应数据")


class Empty(BaseModel):
    """用于显式声明 data 为空对象的响应。"""

    pass


class SuccessResult[T](BaseModel):
    """成功结果包装器

    用于在 ResponseUtil 装饰器中返回自定义的成功消息。

    示例::

        @ResponseUtil(i18n_summary=ApiSummaryI18n.GET_TABLES)
        async def get_tables(file_id: str) -> SuccessResult[GetTablesData]:
            tables = db_service.list_tables()
            return SuccessResult(data=GetTablesData(tables=..., has_placeholder=False))
    """

    data: T = Field(..., description="响应数据")
    i18n_msg: I18nMessage | None = Field(None, description="国际化消息")
    i18n_args: dict[str, Any] = Field(default_factory=dict)


class PageData[T](BaseModel):
    """分页数据容器（不强制 rows 的具体结构，避免热路径过重校验）。"""

    page: int = Field(1, ge=1, description="页码，从 1 开始")
    limit: int = Field(50, ge=1, le=1000, description="每页数量")
    total: int = Field(0, ge=0, description="总数量")
    rows: list[T] = Field(default_factory=list, description="数据列表")


# ========== 请求体模型 ==========


class OpenFileBody(BaseModel):
    """打开数据库文件请求体"""

    path: str = Field(..., description="数据库文件本地路径")


class UpdateNoteBody(BaseModel):
    """更新文件备注请求体"""

    note: str = Field(..., description="备注内容")


class ConvertEngineBody(BaseModel):
    """引擎转换请求体"""

    source_path: str = Field(..., description="源文件路径")
    source_engine: str = Field(..., description="源引擎名称")
    target_engine: str = Field(..., description="目标引擎名称")
    target_path: str = Field(..., description="目标文件路径")


class RenameTableRequest(BaseModel):
    """重命名表请求"""

    new_name: str = Field(..., min_length=1, description="新表名")


class UpdateCommentRequest(BaseModel):
    """更新备注请求"""

    comment: str | None = Field(None, description="新备注（空字符串或 None 表示清空）")


class InsertRowRequest(BaseModel):
    """插入行请求"""

    data: dict[str, Any] = Field(..., description="行数据")


class UpdateRowRequest(BaseModel):
    """更新行请求"""

    pk: Any = Field(..., description="主键值")
    data: dict[str, Any] = Field(..., description="要更新的数据")


class DeleteRowRequest(BaseModel):
    """删除行请求"""

    pk: Any = Field(..., description="主键值")


# ========== 文件相关响应数据模型 ==========


class RecentFilesData(BaseModel):
    """最近文件列表响应数据"""

    files: list[dict[str, Any]] = Field(
        default_factory=list, description="文件记录列表（model_dump 结果）"
    )


class DiscoverFileEntry(BaseModel):
    """发现的文件条目"""

    path: str = Field(..., description="文件绝对路径")
    name: str = Field(..., description="文件名（不含扩展名）")
    extension: str = Field(..., description="文件扩展名")
    size: int = Field(..., description="文件大小（字节）")


class DiscoverFilesData(BaseModel):
    """发现文件响应数据"""

    files: list[DiscoverFileEntry] = Field(
        default_factory=list, description="发现的文件列表"
    )


class OpenFileData(BaseModel):
    """打开文件响应数据"""

    file_id: str = Field(..., description="文件 ID")
    name: str = Field(..., description="文件名")
    path: str = Field(..., description="文件路径")
    file_size: int = Field(..., description="文件大小（字节）")
    engine_name: str = Field(..., description="引擎名称")
    tables_count: int = Field(..., description="表数量")


class UserHomeData(BaseModel):
    """用户主目录响应数据"""

    home: str = Field(..., description="用户主目录路径")


class LastBrowseDirectoryData(BaseModel):
    """最后浏览目录响应数据"""

    directory: str = Field(..., description="目录路径")


class DirectoryEntry(BaseModel):
    """目录浏览条目"""

    name: str = Field(..., description="条目名称")
    path: str = Field(..., description="完整路径")
    type: str = Field(..., description="类型：'file' 或 'dir'")
    size: int | None = Field(None, description="文件大小（字节），目录为 None")
    mtime: float | None = Field(None, description="最后修改时间（时间戳）")


class BrowseDirectoryData(BaseModel):
    """浏览目录响应数据"""

    path: str = Field(..., description="当前目录路径")
    entries: list[DirectoryEntry] = Field(
        default_factory=list, description="目录内容列表"
    )


class AvailableEnginesData(BaseModel):
    """可用引擎列表响应数据"""

    engines: Any = Field(None, description="引擎信息（结构由 pytuck 决定）")


class ConvertEngineData(BaseModel):
    """引擎转换响应数据"""

    tables: int = Field(..., description="转换的表数量")
    records: int = Field(..., description="转换的记录数量")
    target_path: str = Field(..., description="目标文件路径")
    engine_name: str = Field(..., description="目标引擎名称")


# ========== 表/数据相关响应数据模型 ==========


class TableMetadataItem(BaseModel):
    """表元数据条目"""

    name: str = Field(..., description="表名")
    comment: str | None = Field(None, description="表备注")


class GetTablesData(BaseModel):
    """获取表列表响应数据"""

    tables: list[TableMetadataItem] = Field(
        default_factory=list, description="表元数据列表"
    )
    has_placeholder: bool = Field(False, description="是否包含占位符表")


class ColumnSchema(BaseModel):
    """列定义信息"""

    name: str = Field(..., description="列名")
    type: str = Field(..., description="列类型")
    nullable: bool = Field(True, description="是否可空")
    primary_key: bool = Field(False, description="是否为主键")
    default_value: str | None = Field(None, description="默认值")
    comment: str | None = Field(None, description="列备注")
    autoincrement: bool = Field(False, description="是否自增")
    unique: bool = Field(False, description="是否唯一")


class GetTableSchemaData(BaseModel):
    """表结构响应数据"""

    table_name: str = Field(..., description="表名")
    row_count: int = Field(..., description="行数")
    columns: list[ColumnSchema] = Field(default_factory=list, description="列定义列表")
    table_comment: str | None = Field(None, description="表备注")


class RenameTableData(BaseModel):
    """重命名表响应数据"""

    old_name: str = Field(..., description="旧表名")
    new_name: str = Field(..., description="新表名")


class UpdateTableCommentData(BaseModel):
    """更新表备注响应数据"""

    table_name: str = Field(..., description="表名")
    comment: str | None = Field(None, description="备注内容")


class UpdateColumnCommentData(BaseModel):
    """更新列备注响应数据"""

    table_name: str = Field(..., description="表名")
    column_name: str = Field(..., description="列名")
    comment: str | None = Field(None, description="备注内容")


class InsertRowData(BaseModel):
    """插入行响应数据"""

    inserted_pk: Any = Field(..., description="插入记录的主键值")


class UpdateRowData(BaseModel):
    """更新行响应数据"""

    updated: bool = Field(..., description="是否更新成功")
    pk: Any = Field(..., description="更新记录的主键值")


class DeleteRowData(BaseModel):
    """删除行响应数据"""

    deleted: bool = Field(..., description="是否删除成功")
    pk: Any = Field(..., description="删除记录的主键值")


class DropTableData(BaseModel):
    """删除表响应数据"""

    deleted: bool = Field(..., description="是否删除成功")
    table_name: str = Field(..., description="被删除的表名")


class TablePrimaryKeyData(BaseModel):
    """表主键信息响应数据"""

    table_name: str = Field(..., description="表名")
    primary_key: str | None = Field(None, description="主键列名")
    has_primary_key: bool = Field(..., description="是否有主键")
    is_pseudo_pk: bool = Field(..., description="是否为伪主键")


# ========== 过滤器模型（内部使用） ==========


class FilterItem(BaseModel):
    """查询过滤器条目"""

    field: str = Field(..., description="字段名")
    op: str = Field(..., description="操作符")
    value: Any = Field(..., description="过滤值")
