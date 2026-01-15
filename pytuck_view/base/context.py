from contextvars import ContextVar

from ..utils.schemas import ContextInfo

current_context: ContextVar[ContextInfo] = ContextVar("current_context")


class ContextManager:
    """
    上下文管理器
    """

    def __init__(self, context_info: ContextInfo):
        self.context_info = context_info

    def __enter__(self):
        self.__context_token = current_context.set(self.context_info)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        current_context.reset(self.__context_token)
