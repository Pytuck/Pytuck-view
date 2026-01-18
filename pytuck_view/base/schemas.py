"""API Schema 定义

本模块用于：
- 定义统一响应结构 ApiResponse[T]（code/msg/data）
- 定义常用的通用数据模型（分页、列表等）

约定：
- `code` 为业务码：0=成功，1=失败，2=警告
- HTTP status 仍按语义返回（由路由决定）
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, ConfigDict

from pytuck_view.utils.schemas import I18nMessage


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
        async def get_tables(file_id: str) -> SuccessResult[dict]:
            tables = db_service.list_tables()
            if has_placeholder(tables):
                return SuccessResult(
                    data={"tables": tables},
                    i18n_msg=DatabaseI18n.GET_TABLES_WITH_PLACEHOLDER
                )
            return SuccessResult(data={"tables": tables})
    """

    data: T = Field(..., description="响应数据")
    i18n_msg: I18nMessage | None = None
    i18n_args: dict[str, Any] = Field(default_factory=dict)


class PageInfo(BaseModel):
    """分页信息（用于列表接口的通用描述）。"""

    page: int = Field(1, ge=1, description="页码，从 1 开始")
    limit: int = Field(50, ge=1, le=1000, description="每页数量")
    total: int = Field(0, ge=0, description="总数量")


class PageData(BaseModel):
    """分页数据容器（不强制 rows 的具体结构，避免热路径过重校验）。"""

    page: int
    limit: int
    total: int
    rows: list[dict[str, Any]]
