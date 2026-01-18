"""前端国际化消息定义

本模块定义前端 UI 的所有翻译文本。
应用启动时自动生成 JSON 文件到 static/locales/。
"""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FrontendI18nMessage:
    """前端国际化消息"""

    zh_cn: str
    en_us: str


class CommonUI:
    """通用 UI 文本"""

    APP_TITLE = FrontendI18nMessage(
        zh_cn="Pytuck View - 数据库查看器", en_us="Pytuck View - Database Viewer"
    )

    OPEN = FrontendI18nMessage(zh_cn="打开", en_us="Open")
    CLOSE = FrontendI18nMessage(zh_cn="关闭", en_us="Close")
    CONFIRM = FrontendI18nMessage(zh_cn="确认", en_us="Confirm")
    CANCEL = FrontendI18nMessage(zh_cn="取消", en_us="Cancel")
    BROWSE = FrontendI18nMessage(zh_cn="浏览", en_us="Browse")
    LOADING = FrontendI18nMessage(zh_cn="加载中...", en_us="Loading...")
    ERROR = FrontendI18nMessage(zh_cn="错误", en_us="Error")
    SUCCESS = FrontendI18nMessage(zh_cn="成功", en_us="Success")
    YES = FrontendI18nMessage(zh_cn="是", en_us="Yes")
    NO = FrontendI18nMessage(zh_cn="否", en_us="No")
    SEARCH = FrontendI18nMessage(zh_cn="搜索", en_us="Search")
    FILTER = FrontendI18nMessage(zh_cn="过滤", en_us="Filter")
    REFRESH = FrontendI18nMessage(zh_cn="刷新", en_us="Refresh")
    SELECT_DATABASE_HINT = FrontendI18nMessage(
        zh_cn="选择一个 pytuck 数据库文件开始浏览",
        en_us="Select a pytuck database file to start browsing",
    )
    BACK = FrontendI18nMessage(zh_cn="返回", en_us="Back")
    TABLES_COUNT = FrontendI18nMessage(zh_cn="张表", en_us="tables")


class FileUI:
    """文件操作 UI 文本"""

    OPEN_FILE = FrontendI18nMessage(zh_cn="打开文件", en_us="Open File")
    CLOSE_FILE = FrontendI18nMessage(zh_cn="关闭文件", en_us="Close File")
    RECENT_FILES = FrontendI18nMessage(zh_cn="最近文件", en_us="Recent Files")
    BROWSE_DIRECTORY = FrontendI18nMessage(zh_cn="浏览目录", en_us="Browse Directory")
    FILE_NAME = FrontendI18nMessage(zh_cn="文件名", en_us="File Name")
    FILE_SIZE = FrontendI18nMessage(zh_cn="文件大小", en_us="File Size")
    LAST_OPENED = FrontendI18nMessage(zh_cn="最后打开", en_us="Last Opened")
    ENGINE = FrontendI18nMessage(zh_cn="引擎", en_us="Engine")
    NO_FILES_YET = FrontendI18nMessage(
        zh_cn="还没有打开过文件", en_us="No files opened yet"
    )
    SELECT_FILE_TO_VIEW = FrontendI18nMessage(
        zh_cn="请选择一个文件以查看其内容",
        en_us="Please select a file to view its content",
    )


class TableUI:
    """表格操作 UI 文本"""

    TABLE_NAME = FrontendI18nMessage(zh_cn="表名", en_us="Table Name")
    ROW_COUNT = FrontendI18nMessage(zh_cn="行数", en_us="Row Count")
    COLUMNS = FrontendI18nMessage(zh_cn="列", en_us="Columns")
    ROWS = FrontendI18nMessage(zh_cn="数据", en_us="Rows")
    VIEW_DATA = FrontendI18nMessage(zh_cn="查看数据", en_us="View Data")
    FILTER_PLACEHOLDER = FrontendI18nMessage(
        zh_cn="输入过滤条件...", en_us="Enter filter..."
    )
    NO_TABLES = FrontendI18nMessage(zh_cn="没有表", en_us="No tables")
    LOADING_TABLES = FrontendI18nMessage(
        zh_cn="正在加载表列表...", en_us="Loading tables..."
    )
    DATA_TABLES = FrontendI18nMessage(zh_cn="数据表", en_us="Data Tables")
    SELECT_TABLE_HINT = FrontendI18nMessage(
        zh_cn="选择一个表开始浏览", en_us="Select a table to start browsing"
    )
    ROWS_COUNT = FrontendI18nMessage(zh_cn="行数据", en_us="rows")
    TAB_STRUCTURE = FrontendI18nMessage(zh_cn="结构", en_us="Structure")
    TAB_DATA = FrontendI18nMessage(zh_cn="数据", en_us="Data")

    # 表结构列表表头
    COL_NAME = FrontendI18nMessage(zh_cn="列名", en_us="Column Name")
    COL_TYPE = FrontendI18nMessage(zh_cn="数据类型", en_us="Data Type")
    COL_NULLABLE = FrontendI18nMessage(zh_cn="允许空值", en_us="Nullable")
    COL_PRIMARY_KEY = FrontendI18nMessage(zh_cn="主键", en_us="Primary Key")
    COL_DEFAULT = FrontendI18nMessage(zh_cn="默认值", en_us="Default Value")
    COL_COMMENT = FrontendI18nMessage(zh_cn="备注", en_us="Comment")


class NavigationUI:
    """导航 UI 文本"""

    BACK_TO_PARENT = FrontendI18nMessage(zh_cn="返回上级", en_us="Back to Parent")
    HOME = FrontendI18nMessage(zh_cn="主目录", en_us="Home")
    CURRENT_PATH = FrontendI18nMessage(zh_cn="当前路径", en_us="Current Path")


class LanguageUI:
    """语言切换 UI 文本"""

    SWITCH_LANGUAGE = FrontendI18nMessage(zh_cn="切换语言", en_us="Switch Language")
    CHINESE = FrontendI18nMessage(zh_cn="简体中文", en_us="Simplified Chinese")
    ENGLISH = FrontendI18nMessage(zh_cn="英文", en_us="English")


# 导出所有 UI 类用于生成
ALL_UI_CLASSES = [CommonUI, FileUI, TableUI, NavigationUI, LanguageUI]


def generate_locale_json(locale: str) -> dict[str, str]:
    """生成指定语言的翻译字典

    :param locale: 语言代码(zh_cn/en_us)
    :return: key -> 翻译文本的字典
    """
    translations = {}

    for ui_class in ALL_UI_CLASSES:
        class_name = ui_class.__name__  # 如 "CommonUI"
        prefix = class_name.replace("UI", "").lower()  # 如 "common"

        # 遍历类属性
        for attr_name in dir(ui_class):
            if attr_name.startswith("_"):
                continue

            attr_value = getattr(ui_class, attr_name)
            if isinstance(attr_value, FrontendI18nMessage):
                # 将大写字母转换为小写,生成 camelCase key
                # APP_TITLE -> appTitle, BROWSE_DIRECTORY -> browseDirectory
                key_parts = attr_name.split("_")
                camel_name = key_parts[0].lower() + "".join(
                    word.capitalize() for word in key_parts[1:]
                )
                key = f"{prefix}.{camel_name}"
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

        print(f"✓ 生成前端翻译: {locale}.json ({len(translations)} 个)")
