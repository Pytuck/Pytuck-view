"""国际化消息定义

按模块组织所有国际化消息，使用 I18nMessage 对象。
"""

from pytuck_view.utils.schemas import I18nMessage


class CommonI18n:
    """通用国际化消息"""

    SUCCESS = I18nMessage(zh_cn="操作成功", en_us="Operation successful")

    UNEXPECTED_ERROR = I18nMessage(
        zh_cn="[{summary}] 服务器内部错误: {error}",
        en_us="[{summary}] Internal server error: {error}",
    )


class ApiSummaryI18n:
    """API 接口摘要国际化"""

    GET_RECENT_FILES = I18nMessage(zh_cn="获取最近文件列表", en_us="Get recent files")

    DISCOVER_FILES = I18nMessage(
        zh_cn="发现数据库文件", en_us="Discover database files"
    )

    OPEN_FILE = I18nMessage(zh_cn="打开数据库文件", en_us="Open database file")

    CLOSE_FILE = I18nMessage(zh_cn="关闭数据库文件", en_us="Close database file")

    DELETE_RECENT_FILE = I18nMessage(zh_cn="删除历史记录", en_us="Delete recent file")

    GET_USER_HOME = I18nMessage(zh_cn="获取用户主目录", en_us="Get user home")

    GET_LAST_BROWSE_DIRECTORY = I18nMessage(
        zh_cn="获取最后浏览目录", en_us="Get last browse directory"
    )

    BROWSE_DIRECTORY = I18nMessage(zh_cn="浏览目录", en_us="Browse directory")

    GET_TABLES = I18nMessage(zh_cn="获取表列表", en_us="Get tables")

    GET_TABLE_SCHEMA = I18nMessage(zh_cn="获取表结构", en_us="Get table schema")

    GET_TABLE_ROWS = I18nMessage(zh_cn="获取表数据", en_us="Get table rows")

    RENAME_TABLE = I18nMessage(zh_cn="重命名表", en_us="Rename table")

    UPDATE_TABLE_COMMENT = I18nMessage(zh_cn="更新表备注", en_us="Update table comment")

    UPDATE_COLUMN_COMMENT = I18nMessage(
        zh_cn="更新列备注", en_us="Update column comment"
    )

    INSERT_ROW = I18nMessage(zh_cn="插入行", en_us="Insert row")

    UPDATE_ROW = I18nMessage(zh_cn="更新行", en_us="Update row")

    DELETE_ROW = I18nMessage(zh_cn="删除行", en_us="Delete row")


class FileI18n:
    """文件管理模块国际化"""

    # 成功消息

    OPEN_FILE_SUCCESS = I18nMessage(
        zh_cn="文件打开成功", en_us="File opened successfully"
    )

    CLOSE_FILE_SUCCESS = I18nMessage(
        zh_cn="文件已关闭", en_us="File closed successfully"
    )

    DELETE_RECENT_FILE_SUCCESS = I18nMessage(
        zh_cn="历史记录已删除", en_us="Recent file deleted successfully"
    )

    # 错误消息

    FILE_NOT_FOUND = I18nMessage(
        zh_cn="文件不存在: {path}", en_us="File not found: {path}"
    )

    INVALID_DATABASE_FILE = I18nMessage(
        zh_cn="不是有效的 pytuck 数据库文件: {path}",
        en_us="Not a valid pytuck database file: {path}",
    )

    CANNOT_OPEN_FILE = I18nMessage(zh_cn="无法打开文件", en_us="Cannot open file")

    OPEN_FILE_FAILED = I18nMessage(
        zh_cn="打开文件失败: {error}", en_us="Failed to open file: {error}"
    )

    DATABASE_OPEN_FAILED = I18nMessage(
        zh_cn="数据库打开失败", en_us="Failed to open database"
    )

    GET_RECENT_FILES_FAILED = I18nMessage(
        zh_cn="获取最近文件失败: {error}", en_us="Failed to get recent files: {error}"
    )

    HISTORY_NOT_EXISTS = I18nMessage(
        zh_cn="历史记录不存在", en_us="History record not exists"
    )

    GET_USER_HOME_FAILED = I18nMessage(
        zh_cn="无法获取用户主目录: {error}", en_us="Failed to get user home: {error}"
    )

    GET_LAST_BROWSE_DIR_FAILED = I18nMessage(
        zh_cn="获取最后浏览目录失败: {error}",
        en_us="Failed to get last browse directory: {error}",
    )

    BROWSE_DIRECTORY_FAILED = I18nMessage(
        zh_cn="浏览目录失败: {error}", en_us="Failed to browse directory: {error}"
    )

    PATH_NOT_EXISTS = I18nMessage(zh_cn="路径不存在", en_us="Path does not exist")

    NOT_A_DIRECTORY = I18nMessage(zh_cn="不是目录", en_us="Not a directory")

    ACCESS_DENIED = I18nMessage(
        zh_cn="无法访问该目录（权限不足）",
        en_us="Cannot access directory (permission denied)",
    )


class DatabaseI18n:
    """数据库模块国际化"""

    APP_NAME = I18nMessage(zh_cn="Pytuck-view", en_us="Pytuck-view")

    # 错误消息
    DB_NOT_OPENED = I18nMessage(
        zh_cn="数据库文件未打开", en_us="Database file not opened"
    )

    GET_TABLES_FAILED = I18nMessage(
        zh_cn="获取表列表失败: {error}", en_us="Failed to get tables: {error}"
    )

    TABLE_NOT_EXISTS = I18nMessage(
        zh_cn="表 '{table_name}' 不存在", en_us="Table '{table_name}' does not exist"
    )

    GET_SCHEMA_FAILED = I18nMessage(
        zh_cn="获取表结构失败: {error}", en_us="Failed to get schema: {error}"
    )

    GET_ROWS_FAILED = I18nMessage(
        zh_cn="获取表数据失败: {error}", en_us="Failed to get rows: {error}"
    )

    # 自定义成功消息 (用于 SuccessResult)
    GET_TABLES_WITH_PLACEHOLDER = I18nMessage(
        zh_cn="表列表获取成功,但部分功能需要 pytuck 库支持",
        en_us="Tables retrieved successfully, but some features require pytuck library",
    )

    GET_SCHEMA_WITH_PLACEHOLDER = I18nMessage(
        zh_cn="表结构获取成功,但列信息功能需要 pytuck 库完善",
        en_us="Schema retrieved successfully, but column info requires pytuck library",
    )

    GET_ROWS_PLACEHOLDER = I18nMessage(
        zh_cn="数据查询功能暂不可用,需要 pytuck 库支持",
        en_us="Data query not available, requires pytuck library",
    )

    GET_ROWS_WITH_FILTER = I18nMessage(
        zh_cn="表数据获取成功({pagination}),应用了 {filter_count} 个过滤条件",
        en_us=(
            "Rows retrieved successfully ({pagination}), applied {filter_count} filters"
        ),
    )

    GET_ROWS_SUCCESS = I18nMessage(
        zh_cn="表数据获取成功({pagination})",
        en_us="Rows retrieved successfully ({pagination})",
    )

    # Schema 修改成功消息
    RENAME_TABLE_SUCCESS = I18nMessage(
        zh_cn="表重命名成功",
        en_us="Table renamed successfully",
    )

    UPDATE_COMMENT_SUCCESS = I18nMessage(
        zh_cn="备注更新成功",
        en_us="Comment updated successfully",
    )

    # 数据行操作成功消息
    INSERT_ROW_SUCCESS = I18nMessage(
        zh_cn="数据插入成功",
        en_us="Row inserted successfully",
    )

    UPDATE_ROW_SUCCESS = I18nMessage(
        zh_cn="数据更新成功",
        en_us="Row updated successfully",
    )

    DELETE_ROW_SUCCESS = I18nMessage(
        zh_cn="数据删除成功",
        en_us="Row deleted successfully",
    )

    # 数据行操作错误消息
    NO_PRIMARY_KEY = I18nMessage(
        zh_cn="该表没有主键，无法执行此操作",
        en_us="This table has no primary key, cannot perform this operation",
    )

    DUPLICATE_KEY = I18nMessage(
        zh_cn="主键 '{pk}' 已存在",
        en_us="Primary key '{pk}' already exists",
    )

    INSERT_FAILED = I18nMessage(
        zh_cn="插入数据失败: {error}",
        en_us="Insert failed: {error}",
    )

    UPDATE_FAILED = I18nMessage(
        zh_cn="更新数据失败: {error}",
        en_us="Update failed: {error}",
    )

    DELETE_FAILED = I18nMessage(
        zh_cn="删除数据失败: {error}",
        en_us="Delete failed: {error}",
    )

    RENAME_TABLE_FAILED = I18nMessage(
        zh_cn="重命名表失败: {error}",
        en_us="Rename table failed: {error}",
    )

    UPDATE_COMMENT_FAILED = I18nMessage(
        zh_cn="更新备注失败: {error}",
        en_us="Update comment failed: {error}",
    )
