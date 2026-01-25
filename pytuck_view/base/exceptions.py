"""统一异常类

提供应用级异常基类和具体异常类型，支持国际化消息。
"""

from typing import Any

from pytuck_view.utils.schemas import I18nMessage


class AppException(Exception):
    """应用异常基类

    所有业务异常都应继承此类，并提供国际化消息。

    示例::

        raise ServiceException(
            FileI18n.FILE_NOT_FOUND,
            path="/some/path"
        )
    """

    def __init__(
        self, i18n_msg: I18nMessage, data: Any = None, **format_args: Any
    ) -> None:
        """初始化异常

        :param i18n_msg: 国际化消息对象
        :param data: 附带的数据（可选）
        :param format_args: 消息格式化参数
        """
        self.i18n_msg = i18n_msg
        self.data = data
        self.format_args = format_args
        super().__init__(i18n_msg.zh_cn)

    def translate(self, lang: str) -> str:
        """翻译消息为指定语言

        :param lang: 语言代码（如 'zh_cn', 'en_us'）
        :return: 翻译后的消息
        """
        return self.i18n_msg.format(lang, **self.format_args)


class ServiceException(AppException):
    """业务异常（code=1）

    用于表示业务逻辑错误，如资源未找到、权限不足等。
    """

    pass


class ResultWarningException(AppException):
    """结果警告（code=2）

    用于任何结果为警告级别的错误
    """

    pass
