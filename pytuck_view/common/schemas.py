"""
基础数据模型
"""
from pydantic import BaseModel, Field


class I18nMessage(BaseModel):
    """
    数据模型：国际化语言包

    - 采用f-string模板
    - 未匹配则默认用中文
    """
    zh_cn: str = Field(..., description="中文消息模板")
    en_us: str = Field(..., description="英文消息模板")

    def get_template(self, lang: str) -> str:
        """获取指定语言的消息模板"""
        return getattr(self, lang.lower(), self.zh_cn)

    def format(self, lang: str, **kwargs):
        """格式化消息模板"""
        template = self.get_template(lang)
        try:
            return template.format(**kwargs)
        except KeyError:
            return template
