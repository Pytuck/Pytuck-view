import json
from pathlib import Path

from pytuck_view.base.constants import HOME_DIR
from pytuck_view.base.frontend_i18n import ALL_UI_CLASSES
from pytuck_view.utils.logger import logger
from pytuck_view.utils.schemas import I18nMessage


def generate_locale_json(locale: str) -> dict[str, str]:
    """生成指定语言的翻译字典

    :param locale: 语言代码(zh_cn/en_us)
    :return: key -> 翻译文本的字典
    """
    translations = {}

    for ui_class in ALL_UI_CLASSES:
        prefix = ui_class.__i18n_prefix__

        # 遍历类属性
        for attr_name in dir(ui_class):
            if attr_name.startswith("_"):
                continue

            attr_value = getattr(ui_class, attr_name)
            if isinstance(attr_value, I18nMessage):
                # 直接使用 prefix.key 拼接，无任何转换
                key = f"{prefix}.{attr_value.key}"
                # 获取对应语言的翻译
                translation = getattr(attr_value, locale)
                translations[key] = translation

    return translations


def generate_all_locales(output_dir: Path) -> None:
    """生成所有语言的 JSON 文件

    :param output_dir: 输出目录(static/locales)
    """

    # 确保输出目录存在
    output_dir.mkdir(parents=True, exist_ok=True)

    # 支持的语言列表
    locales = ["zh_cn", "en_us"]

    for locale in locales:
        # 生成翻译字典
        translations = generate_locale_json(locale)

        # 写入 JSON 文件
        output_file = output_dir / f"{locale}.json"
        with output_file.open("w", encoding="utf-8") as f:
            json.dump(translations, f, ensure_ascii=False, indent=2)

        logger.info(f"✓ 生成前端翻译: {locale}.json ({len(translations)} 个)")


def setup_all() -> None:
    """前置操作"""

    try:
        HOME_DIR.mkdir(exist_ok=True)
        locales_dir = HOME_DIR / "locales"
        generate_all_locales(locales_dir)
    except Exception as e:
        logger.warning(f"警告: 生成前端翻译文件失败: {e}")
        # 不影响应用启动,继续执行
