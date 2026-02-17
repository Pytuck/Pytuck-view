from contextlib import contextmanager
from contextvars import ContextVar, Token

from ..utils.schemas import ContextInfo

current_context: ContextVar[ContextInfo] = ContextVar("current_context")


@contextmanager
def context_manager(context_info: ContextInfo):
    """
    上下文管理器
    """
    context_token: Token[ContextInfo] | None = None
    try:
        context_token = current_context.set(context_info)
        yield
    finally:
        if context_token is not None:
            current_context.reset(context_token)