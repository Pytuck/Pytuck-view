"""API Schema 定义

本模块用于：
- 定义统一响应结构 ApiResponse[T]（code/msg/data）
- 定义常用的通用数据模型（分页、列表等）

约定：
- `code` 为业务码：0=成功，1=失败，2=警告
- HTTP status 仍按语义返回（由路由决定）
"""

from typing import Any
from pydantic import BaseModel, Field


class ApiResponse[T](BaseModel):
    """统一响应模型（泛型）。"""

    code: int = Field(0, description="业务码：0=成功，1=失败，2=警告")
    msg: str = Field("OK", description="提示信息")
    data: T | None = Field(None, description="响应数据")


def ok[T](data: T | None = None, msg: str = "OK") -> ApiResponse[T]:
    """成功响应（code=0）。"""

    return ApiResponse(code=0, msg=msg, data=data)


def fail[T](msg: str, data: T | None = None, code: int = 1) -> ApiResponse[T]:
    """失败响应（默认 code=1）。"""

    return ApiResponse(code=code, msg=msg, data=data)


def warn[T](msg: str, data: T | None = None) -> ApiResponse[T]:
    """警告响应（code=2）。"""

    return ApiResponse(code=2, msg=msg, data=data)


class Empty(BaseModel):
    """用于显式声明 data 为空对象的响应。"""

    pass


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
