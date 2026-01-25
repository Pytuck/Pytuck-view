"""前端国际化消息定义

本模块定义前端 UI 的所有翻译文本。
应用启动时自动生成 JSON 文件到 static/locales/。
"""

from typing import Any

from pytuck_view.utils.schemas import I18nMessage

ALL_UI_CLASSES: list[type["BaseUIClass"]] = []


class BaseUIClass:
    """前端 UI 翻译类的基类

    所有包含前端翻译文本的类都应继承此基类，
    以便自动被收集到翻译生成流程中。
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        ALL_UI_CLASSES.append(cls)
        super().__init_subclass__(**kwargs)


class CommonUI(BaseUIClass):
    """通用 UI 文本"""

    APP_TITLE = I18nMessage(
        zh_cn="Pytuck View - 数据库查看器", en_us="Pytuck View - Database Viewer"
    )

    OPEN = I18nMessage(zh_cn="打开", en_us="Open")
    CLOSE = I18nMessage(zh_cn="关闭", en_us="Close")
    CONFIRM = I18nMessage(zh_cn="确认", en_us="Confirm")
    CANCEL = I18nMessage(zh_cn="取消", en_us="Cancel")
    BROWSE = I18nMessage(zh_cn="浏览", en_us="Browse")
    LOADING = I18nMessage(zh_cn="加载中...", en_us="Loading...")
    ERROR = I18nMessage(zh_cn="错误", en_us="Error")
    SUCCESS = I18nMessage(zh_cn="成功", en_us="Success")
    YES = I18nMessage(zh_cn="是", en_us="Yes")
    NO = I18nMessage(zh_cn="否", en_us="No")
    SEARCH = I18nMessage(zh_cn="搜索", en_us="Search")
    FILTER = I18nMessage(zh_cn="过滤", en_us="Filter")
    REFRESH = I18nMessage(zh_cn="刷新", en_us="Refresh")
    SELECT_DATABASE_HINT = I18nMessage(
        zh_cn="选择一个 pytuck 数据库文件开始浏览",
        en_us="Select a pytuck database file to start browsing",
    )
    BACK = I18nMessage(zh_cn="返回", en_us="Back")
    TABLES_COUNT = I18nMessage(zh_cn="张表", en_us="tables")


class FileUI(BaseUIClass):
    """文件操作 UI 文本"""

    OPEN_FILE = I18nMessage(zh_cn="打开文件", en_us="Open File")
    CLOSE_FILE = I18nMessage(zh_cn="关闭文件", en_us="Close File")
    RECENT_FILES = I18nMessage(zh_cn="最近文件", en_us="Recent Files")
    BROWSE_DIRECTORY = I18nMessage(zh_cn="浏览目录", en_us="Browse Directory")
    FILE_NAME = I18nMessage(zh_cn="文件名", en_us="File Name")
    FILE_SIZE = I18nMessage(zh_cn="文件大小", en_us="File Size")
    LAST_OPENED = I18nMessage(zh_cn="最后打开", en_us="Last Opened")
    ENGINE = I18nMessage(zh_cn="引擎", en_us="Engine")
    NO_FILES_YET = I18nMessage(
        zh_cn="还没有添加过文件", en_us="No files added yet"
    )
    SELECT_FILE_TO_VIEW = I18nMessage(
        zh_cn="请选择一个文件以查看其内容",
        en_us="Please select a file to view its content",
    )

    # 文件浏览器
    SELECT_DATABASE_FILE = I18nMessage(
        zh_cn="选择数据库文件", en_us="Select Database File"
    )
    PARENT_DIRECTORY = I18nMessage(zh_cn="上级目录", en_us="Parent Directory")
    GO_TO = I18nMessage(zh_cn="前往", en_us="Go")


class TableUI(BaseUIClass):
    """表格操作 UI 文本"""

    TABLE_NAME = I18nMessage(zh_cn="表名", en_us="Table Name")
    ROW_COUNT = I18nMessage(zh_cn="行数", en_us="Row Count")
    COLUMNS = I18nMessage(zh_cn="列", en_us="Columns")
    ROWS = I18nMessage(zh_cn="数据", en_us="Rows")
    VIEW_DATA = I18nMessage(zh_cn="查看数据", en_us="View Data")
    FILTER_PLACEHOLDER = I18nMessage(
        zh_cn="输入过滤条件...", en_us="Enter filter..."
    )
    NO_TABLES = I18nMessage(zh_cn="没有表", en_us="No tables")
    LOADING_TABLES = I18nMessage(
        zh_cn="正在加载表列表...", en_us="Loading tables..."
    )
    DATA_TABLES = I18nMessage(zh_cn="数据表", en_us="Data Tables")
    SELECT_TABLE_HINT = I18nMessage(
        zh_cn="选择一个表开始浏览", en_us="Select a table to start browsing"
    )
    ROWS_COUNT = I18nMessage(zh_cn="行数据", en_us="rows")
    TAB_STRUCTURE = I18nMessage(zh_cn="结构", en_us="Structure")
    TAB_DATA = I18nMessage(zh_cn="数据", en_us="Data")

    # 表结构列表表头
    COL_NAME = I18nMessage(zh_cn="列名", en_us="Column Name")
    COL_TYPE = I18nMessage(zh_cn="数据类型", en_us="Data Type")
    COL_NULLABLE = I18nMessage(zh_cn="允许空值", en_us="Nullable")
    COL_PRIMARY_KEY = I18nMessage(zh_cn="主键", en_us="Primary Key")
    COL_DEFAULT = I18nMessage(zh_cn="默认值", en_us="Default Value")
    COL_COMMENT = I18nMessage(zh_cn="备注", en_us="Comment")


class NavigationUI(BaseUIClass):
    """导航 UI 文本"""

    BACK_TO_PARENT = I18nMessage(zh_cn="返回上级", en_us="Back to Parent")
    HOME = I18nMessage(zh_cn="主目录", en_us="Home")
    CURRENT_PATH = I18nMessage(zh_cn="当前路径", en_us="Current Path")


class LanguageUI(BaseUIClass):
    """语言切换 UI 文本"""

    SWITCH_LANGUAGE = I18nMessage(zh_cn="切换语言", en_us="Switch Language")
    CHINESE = I18nMessage(zh_cn="简体中文", en_us="Simplified Chinese")
    ENGLISH = I18nMessage(zh_cn="英文", en_us="English")


class ErrorUI(BaseUIClass):
    """错误消息 UI 文本"""

    OPEN_FILE_FAILED = I18nMessage(
        zh_cn="打开文件失败", en_us="Failed to open file"
    )
    REMOVE_FAILED = I18nMessage(zh_cn="移除失败", en_us="Failed to remove")
    CANNOT_OPEN_FILE_BROWSER = I18nMessage(
        zh_cn="无法打开文件浏览器", en_us="Cannot open file browser"
    )
    LOAD_TABLE_DATA_FAILED = I18nMessage(
        zh_cn="加载表数据失败", en_us="Failed to load table data"
    )

