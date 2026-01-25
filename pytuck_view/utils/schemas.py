"""
基础数据模型
"""

from typing import ClassVar

from pydantic import BaseModel, Field


class I18nMessage(BaseModel):
    """
    数据模型：国际化语言包

    - 采用f-string模板
    - 支持多种语言标识格式（如 zh-CN, zh_cn, zh 等）
    - 未匹配则默认用中文
    """

    zh_cn: str = Field(..., description="中文消息模板")
    en_us: str = Field(..., description="英文消息模板")

    # 语言别名映射：多种格式 -> canonical field name
    _LANG_ALIASES: ClassVar[dict[str, str]] = {
        # 中文别名
        "zh_cn": "zh_cn",
        "zh-cn": "zh_cn",
        "zh": "zh_cn",
        "chinese": "zh_cn",
        # 英文别名
        "en_us": "en_us",
        "en-us": "en_us",
        "en": "en_us",
        "english": "en_us",
    }

    def _normalize_lang(self, lang: str) -> str:
        """将语言标识规范化为 canonical field name"""
        key = lang.strip().lower()
        return self._LANG_ALIASES.get(key, "zh_cn")

    def get_template(self, lang: str) -> str:
        """获取指定语言的消息模板"""
        canonical = self._normalize_lang(lang)
        return getattr(self, canonical, self.zh_cn)

    def format(self, lang: str, **kwargs: str) -> str:
        """格式化消息模板"""
        template = self.get_template(lang)
        try:
            return template.format(**kwargs)
        except KeyError:
            return template


class ContextInfo(BaseModel):
    """
    数据模型：上下文信息
    - 描述当前请求的上下文信息
    """

    language: str = Field(..., description="当前语言")
