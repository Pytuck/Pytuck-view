from contextvars import ContextVar, Token

from ..utils.schemas import ContextInfo

current_context: ContextVar[ContextInfo] = ContextVar("current_context")


class ContextManager:
    """
    上下文管理器
    """

    def __init__(self, context_info: ContextInfo) -> None:
        self.context_info = context_info
        self.__context_token: Token[ContextInfo] | None = None

    def __enter__(self) -> "ContextManager":
        self.__context_token = current_context.set(self.context_info)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        if self.__context_token is not None:
            current_context.reset(self.__context_token)
