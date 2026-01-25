"""中间件：请求上下文注入

当前仅负责一件事：把 language 写入 ContextInfo，并注入到 ContextVar。

解析优先级：
1) query 参数 lang
2) Header: X-Language
3) Header: Accept-Language
4) 默认：zh_cn

注意：
- 使用 ContextManager 来设置/重置上下文。
- 不做日志、不落盘。
"""

from collections.abc import Callable, Coroutine

from fastapi import Request, Response

from ..utils.schemas import ContextInfo
from .context import ContextManager


def _parse_language(request: Request) -> str:
    lang = request.query_params.get("lang")
    if lang:
        return lang

    lang = request.headers.get("X-Language")
    if lang:
        return lang

    accept_language = request.headers.get("Accept-Language")
    if accept_language:
        # 取第一个语言标签，忽略 q 权重
        first = accept_language.split(",", 1)[0].strip()
        if first:
            return first

    return "zh_cn"


async def language_context_middleware(
    request: Request,
    call_next: Callable[[Request], Coroutine[object, object, Response]],
) -> Response:
    """语言中间件"""
    context_info = ContextInfo(language=_parse_language(request))
    with ContextManager(context_info):
        return await call_next(request)
