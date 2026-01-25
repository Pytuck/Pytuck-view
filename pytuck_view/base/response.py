"""统一响应装饰器

提供 @api_response 装饰器，自动处理异常捕获、消息翻译和响应格式化。
"""

import functools
from collections.abc import Callable, Coroutine
from inspect import iscoroutinefunction
from typing import Any

from pytuck_view.base.context import current_context
from pytuck_view.base.exceptions import (
    AppException,
    ResultWarningException,
)
from pytuck_view.base.i18n import CommonI18n
from pytuck_view.base.schemas import ApiResponse, SuccessResult
from pytuck_view.utils.logger import logger
from pytuck_view.utils.schemas import I18nMessage
from pytuck_view.utils.tiny_func import simplify_exception


def get_current_lang() -> str:
    """获取当前请求的语言

    从 ContextVar 中获取语言设置，默认返回中文。

    :return: 语言代码（如 'zh_cn', 'en_us'）
    """
    try:
        context = current_context.get()
        return context.language
    except LookupError:
        return "zh_cn"


class ResponseUtil[T]:
    """
    返回 json 结果组装

    装饰器用法示例::

        # 使用 I18nMessage 对象，`[User]` 可以不写
        @ResponseUtil[User](i18n_summary=UserI18n.API_CREATE)
        async def create_user():
            # 不需要写 try... except
            # 返回 pydantic 模型实例，或者任意数据（None/bool/str/dict等），
            # 不能返回非数据对象（如文件对象）
            return User(id=1, name='张三')

    """

    @staticmethod
    def success(data: Any = None, msg: str = "success") -> ApiResponse[Any]:
        """成功响应"""
        return ApiResponse(data=data, msg=msg, code=0)

    @staticmethod
    def fail(msg: str, code: int = 1, data: Any = None) -> ApiResponse[Any]:
        """失败响应"""
        return ApiResponse(msg=msg, code=code, data=data)

    @staticmethod
    def warning(msg: str, code: int = 2, data: Any = None) -> ApiResponse[Any]:
        """警告响应"""
        return ApiResponse(msg=msg, code=code, data=data)

    @staticmethod
    def error(msg: str, code: int = -1, data: Any = None) -> ApiResponse[Any]:
        """错误响应

        :param msg: 消息内容
        :param code: 响应码
        :param data: 响应数据，任何数据
        :return: 构建的响应结构模型实例
        """
        return ApiResponse(msg=msg, code=code, data=data)

    def __init__(self, i18n_summary: I18nMessage) -> None:
        """
        返回结果装饰器，将返回值统一为ApiResponse。

        - 正常返回时，应返回一个结果值作为data，返回 success（code=0）。

        发生错误时依次捕获：
            - 发生 ResultWaringException 时，
              直接根据该错误承载的 i18n 信息返回 waring（code=2）。
            - 发生 AppException 时，
              直接根据该错误承载的 i18n 信息返回 error（code=1）。
            - 发生其他 Exception 时，
              返回 error（code=1），记录日志，返回固定格式的国际化。

        :param i18n_summary: 接口操作名称的国际化对象
        """
        assert isinstance(i18n_summary, I18nMessage), (
            "i18n_summary 参数必须是 I18nMessage 对象"
        )
        self.i18n_summary = i18n_summary

    @property
    def lang(self) -> str:
        """获取当前语言（每次请求时实时获取，不缓存）"""
        return get_current_lang()

    @property
    def summary(self) -> str:
        """获取 summary（每次请求时实时获取，不缓存）"""
        return self.i18n_summary.get_template(self.lang)

    def translate_exception(self, e: AppException) -> str:
        """异常消息翻译方法"""
        return e.translate(self.lang)

    def translate_unexpected_error(self, e: Exception) -> str:
        """未预期错误消息翻译方法"""
        return CommonI18n.UNEXPECTED_ERROR.format(
            self.lang, error=str(e), summary=self.summary
        )

    def translate_success_message(self, result: SuccessResult[Any] | Any) -> str:
        """获取成功消息"""
        if isinstance(result, SuccessResult) and result.i18n_msg:
            return result.i18n_msg.format(self.lang, **result.i18n_args)
        return "success"

    @staticmethod
    def _extract_data(result: SuccessResult[Any] | Any) -> Any:
        """提取数据

        :param result: 结果对象(SuccessResult 或普通数据)
        :return: 实际数据
        """
        return result.data if isinstance(result, SuccessResult) else result

    def __call__[**P](
        self, func: Callable[P, Coroutine[Any, Any, Any]]
    ) -> Callable[P, Coroutine[Any, Any, ApiResponse[Any]]]:
        """装饰器主逻辑：自动实现国际化、错误捕获、日志记录"""
        # 异步方法
        if iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> ApiResponse[Any]:
                try:
                    result = await func(*args, **kwargs)
                    data = self._extract_data(result)
                    msg = self.translate_success_message(result)
                    return self.success(data=data, msg=msg)
                except ResultWarningException as e:
                    return self.warning(msg=self.translate_exception(e), data=e.data)
                except AppException as e:
                    return self.fail(msg=self.translate_exception(e), data=e.data)
                except Exception as e:
                    logger.error(
                        f"{self.summary} 发生预期之外的错误：\n{simplify_exception(e)}"
                    )
                    return self.error(self.translate_unexpected_error(e))

            return async_wrapper

        # 同步方法
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> ApiResponse[Any]:
            try:
                result = func(*args, **kwargs)
                data = self._extract_data(result)
                msg = self.translate_success_message(result)
                return self.success(data=data, msg=msg)
            except ResultWarningException as e:
                return self.warning(msg=self.translate_exception(e), data=e.data)
            except AppException as e:
                return self.fail(msg=self.translate_exception(e), data=e.data)
            except Exception as e:
                logger.error(
                    f"{self.summary} 发生预期之外的错误：\n{simplify_exception(e)}"
                )
                return self.error(self.translate_unexpected_error(e))

        return wrapper  # type: ignore[return-value]
