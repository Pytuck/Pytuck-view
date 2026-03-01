"""前端国际化消息定义

本模块定义前端 UI 的所有翻译文本。
应用启动时自动生成 JSON 文件到 static/locales/。

前端 key 规则：{__i18n_prefix__}.{I18nMessage.key}
- 类定义 __i18n_prefix__ = "dataEdit"
- 消息定义 key="addRow"
- 生成的 JSON key 为 "dataEdit.addRow"
"""

from typing import Any

from pytuck_view.utils.schemas import I18nMessage

ALL_UI_CLASSES: list[type["BaseUIClass"]] = []


class BaseUIClass:
    """前端 UI 翻译类的基类

    所有包含前端翻译文本的类都应继承此基类，
    以便自动被收集到翻译生成流程中。

    子类必须定义 __i18n_prefix__ 类属性，
    且所有 I18nMessage 必须定义 key 属性。
    """

    __i18n_prefix__: str = ""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        # 检查 prefix 是否定义
        prefix = getattr(cls, "__i18n_prefix__", "")
        if not prefix:
            raise ValueError(f"{cls.__name__} 必须定义 __i18n_prefix__")

        # 检查所有 I18nMessage 是否定义了 key
        for attr_name in dir(cls):
            if attr_name.startswith("_"):
                continue
            attr_value = getattr(cls, attr_name, None)
            if isinstance(attr_value, I18nMessage) and attr_value.key is None:
                raise ValueError(f"{cls.__name__}.{attr_name} 必须定义 key 属性")

        ALL_UI_CLASSES.append(cls)
        super().__init_subclass__(**kwargs)


class CommonUI(BaseUIClass):
    """通用 UI 文本"""

    __i18n_prefix__ = "common"

    APP_TITLE = I18nMessage(
        key="appTitle",
        zh_cn="Pytuck View - 数据库查看器",
        en_us="Pytuck View - Database Viewer",
    )

    OPEN = I18nMessage(key="open", zh_cn="打开", en_us="Open")
    CLOSE = I18nMessage(key="close", zh_cn="关闭", en_us="Close")
    COPY = I18nMessage(key="copy", zh_cn="复制", en_us="Copy")
    CONFIRM = I18nMessage(key="confirm", zh_cn="确认", en_us="Confirm")
    CANCEL = I18nMessage(key="cancel", zh_cn="取消", en_us="Cancel")
    BROWSE = I18nMessage(key="browse", zh_cn="浏览", en_us="Browse")
    LOADING = I18nMessage(key="loading", zh_cn="加载中...", en_us="Loading...")
    ERROR = I18nMessage(key="error", zh_cn="错误", en_us="Error")
    SUCCESS = I18nMessage(key="success", zh_cn="成功", en_us="Success")
    YES = I18nMessage(key="yes", zh_cn="是", en_us="Yes")
    NO = I18nMessage(key="no", zh_cn="否", en_us="No")
    SEARCH = I18nMessage(key="search", zh_cn="搜索", en_us="Search")
    FILTER = I18nMessage(key="filter", zh_cn="过滤", en_us="Filter")
    REFRESH = I18nMessage(key="refresh", zh_cn="刷新", en_us="Refresh")
    SELECT_DATABASE_HINT = I18nMessage(
        key="selectDatabaseHint",
        zh_cn="选择一个 pytuck 数据库文件开始浏览",
        en_us="Select a pytuck database file to start browsing",
    )
    BACK = I18nMessage(key="back", zh_cn="返回", en_us="Back")
    TABLES_COUNT = I18nMessage(key="tablesCount", zh_cn="张表", en_us="tables")


class FileUI(BaseUIClass):
    """文件操作 UI 文本"""

    __i18n_prefix__ = "file"

    OPEN_FILE = I18nMessage(key="openFile", zh_cn="打开文件", en_us="Open File")
    CLOSE_FILE = I18nMessage(key="closeFile", zh_cn="关闭文件", en_us="Close File")
    RECENT_FILES = I18nMessage(
        key="recentFiles", zh_cn="最近文件", en_us="Recent Files"
    )
    BROWSE_DIRECTORY = I18nMessage(
        key="browseDirectory", zh_cn="浏览目录", en_us="Browse Directory"
    )
    FILE_NAME = I18nMessage(key="fileName", zh_cn="文件名", en_us="File Name")
    FILE_SIZE = I18nMessage(key="fileSize", zh_cn="文件大小", en_us="File Size")
    LAST_OPENED = I18nMessage(key="lastOpened", zh_cn="最后打开", en_us="Last Opened")
    ENGINE = I18nMessage(key="engine", zh_cn="引擎", en_us="Engine")
    NO_FILES_YET = I18nMessage(
        key="noFilesYet", zh_cn="还没有添加过文件", en_us="No files added yet"
    )
    SELECT_FILE_TO_VIEW = I18nMessage(
        key="selectFileToView",
        zh_cn="请选择一个文件以查看其内容",
        en_us="Please select a file to view its content",
    )

    # 文件备注
    NOTE = I18nMessage(key="note", zh_cn="备注", en_us="Note")
    NOTE_PLACEHOLDER = I18nMessage(
        key="notePlaceholder", zh_cn="添加备注...", en_us="Add note..."
    )

    # 文件浏览器
    SELECT_DATABASE_FILE = I18nMessage(
        key="selectDatabaseFile", zh_cn="选择数据库文件", en_us="Select Database File"
    )
    PARENT_DIRECTORY = I18nMessage(
        key="parentDirectory", zh_cn="上级目录", en_us="Parent Directory"
    )
    GO_TO = I18nMessage(key="goTo", zh_cn="前往", en_us="Go")


class TableUI(BaseUIClass):
    """表格操作 UI 文本"""

    __i18n_prefix__ = "table"

    TABLE_NAME = I18nMessage(key="tableName", zh_cn="表名", en_us="Table Name")
    ROW_COUNT = I18nMessage(key="rowCount", zh_cn="行数", en_us="Row Count")
    COLUMNS = I18nMessage(key="columns", zh_cn="列", en_us="Columns")
    ROWS = I18nMessage(key="rows", zh_cn="数据", en_us="Rows")
    VIEW_DATA = I18nMessage(key="viewData", zh_cn="查看数据", en_us="View Data")
    FILTER_PLACEHOLDER = I18nMessage(
        key="filterPlaceholder", zh_cn="输入过滤条件...", en_us="Enter filter..."
    )
    NO_TABLES = I18nMessage(key="noTables", zh_cn="没有表", en_us="No tables")
    LOADING_TABLES = I18nMessage(
        key="loadingTables", zh_cn="正在加载表列表...", en_us="Loading tables..."
    )
    DATA_TABLES = I18nMessage(key="dataTables", zh_cn="数据表", en_us="Data Tables")
    SELECT_TABLE_HINT = I18nMessage(
        key="selectTableHint",
        zh_cn="选择一个表开始浏览",
        en_us="Select a table to start browsing",
    )
    ROWS_COUNT = I18nMessage(key="rowsCount", zh_cn="行数据", en_us="rows")
    TAB_STRUCTURE = I18nMessage(key="tabStructure", zh_cn="结构", en_us="Structure")
    TAB_DATA = I18nMessage(key="tabData", zh_cn="数据", en_us="Data")

    # 表结构列表表头
    COL_NAME = I18nMessage(key="colName", zh_cn="列名", en_us="Column Name")
    COL_TYPE = I18nMessage(key="colType", zh_cn="数据类型", en_us="Data Type")
    COL_NULLABLE = I18nMessage(key="colNullable", zh_cn="允许空值", en_us="Nullable")
    COL_PRIMARY_KEY = I18nMessage(
        key="colPrimaryKey", zh_cn="主键", en_us="Primary Key"
    )
    COL_DEFAULT = I18nMessage(key="colDefault", zh_cn="默认值", en_us="Default Value")
    COL_COMMENT = I18nMessage(key="colComment", zh_cn="备注", en_us="Comment")


class NavigationUI(BaseUIClass):
    """导航 UI 文本"""

    __i18n_prefix__ = "navigation"

    BACK_TO_PARENT = I18nMessage(
        key="backToParent", zh_cn="返回上级", en_us="Back to Parent"
    )
    HOME = I18nMessage(key="home", zh_cn="主目录", en_us="Home")
    CURRENT_PATH = I18nMessage(
        key="currentPath", zh_cn="当前路径", en_us="Current Path"
    )


class LanguageUI(BaseUIClass):
    """语言切换 UI 文本"""

    __i18n_prefix__ = "language"

    SWITCH_LANGUAGE = I18nMessage(
        key="switchLanguage", zh_cn="切换语言", en_us="Switch Language"
    )
    CHINESE = I18nMessage(key="chinese", zh_cn="简体中文", en_us="Simplified Chinese")
    ENGLISH = I18nMessage(key="english", zh_cn="英文", en_us="English")


class ErrorUI(BaseUIClass):
    """错误消息 UI 文本"""

    __i18n_prefix__ = "error"

    OPEN_FILE_FAILED = I18nMessage(
        key="openFileFailed", zh_cn="打开文件失败", en_us="Failed to open file"
    )
    REMOVE_FAILED = I18nMessage(
        key="removeFailed", zh_cn="移除失败", en_us="Failed to remove"
    )
    CANNOT_OPEN_FILE_BROWSER = I18nMessage(
        key="cannotOpenFileBrowser",
        zh_cn="无法打开文件浏览器",
        en_us="Cannot open file browser",
    )
    LOAD_TABLE_DATA_FAILED = I18nMessage(
        key="loadTableDataFailed",
        zh_cn="加载表数据失败",
        en_us="Failed to load table data",
    )


class DataEditUI(BaseUIClass):
    """数据编辑 UI 文本"""

    __i18n_prefix__ = "dataEdit"

    # 操作按钮
    ACTIONS = I18nMessage(key="actions", zh_cn="操作", en_us="Actions")
    SAVE = I18nMessage(key="save", zh_cn="保存", en_us="Save")
    EDIT = I18nMessage(key="edit", zh_cn="编辑", en_us="Edit")
    DELETE = I18nMessage(key="delete", zh_cn="删除", en_us="Delete")
    REMOVE = I18nMessage(key="remove", zh_cn="移除", en_us="Remove")

    # 视图模式
    TABLE_VIEW = I18nMessage(key="tableView", zh_cn="表格", en_us="Table")
    RECORD_VIEW = I18nMessage(key="recordView", zh_cn="记录", en_us="Record")

    # 新增行
    ADD_ROW = I18nMessage(key="addRow", zh_cn="新增行", en_us="Add Row")
    NEW_RECORD = I18nMessage(key="newRecord", zh_cn="新增记录", en_us="New Record")

    # 表/列编辑
    INPUT_TABLE_COMMENT = I18nMessage(
        key="inputTableComment", zh_cn="输入表备注...", en_us="Enter table comment..."
    )
    EDIT_TABLE_NAME = I18nMessage(
        key="editTableName", zh_cn="编辑表名", en_us="Edit table name"
    )
    EDIT_COMMENT = I18nMessage(
        key="editComment", zh_cn="编辑备注", en_us="Edit comment"
    )
    ADD_COMMENT = I18nMessage(key="addComment", zh_cn="添加备注", en_us="Add comment")
    NO_COMMENT = I18nMessage(key="noComment", zh_cn="无备注", en_us="No comment")

    # 主键相关
    NO_PRIMARY_KEY = I18nMessage(
        key="noPrimaryKey", zh_cn="无主键", en_us="No primary key"
    )
    NO_PK_EDIT_LIMIT = I18nMessage(
        key="noPkEditLimit",
        zh_cn="无主键，编辑/删除功能受限",
        en_us="No primary key, edit/delete limited",
    )
    PRIMARY_KEY = I18nMessage(key="primaryKey", zh_cn="主键", en_us="Primary Key")
    USING_INTERNAL_ROWID = I18nMessage(
        key="usingInternalRowId",
        zh_cn="使用内部行号",
        en_us="Using internal row ID",
    )

    # 记录视图导航
    PREV_RECORD = I18nMessage(key="prevRecord", zh_cn="上一条", en_us="Previous")
    NEXT_RECORD = I18nMessage(key="nextRecord", zh_cn="下一条", en_us="Next")
    RECORD_COUNTER = I18nMessage(
        key="recordCounter",
        zh_cn="第 {current} / {total} 条",
        en_us="Record {current} of {total}",
    )

    # 分页
    FIRST_PAGE = I18nMessage(key="firstPage", zh_cn="首页", en_us="First")
    PREV_PAGE = I18nMessage(key="prevPage", zh_cn="上一页", en_us="Previous")
    NEXT_PAGE = I18nMessage(key="nextPage", zh_cn="下一页", en_us="Next")
    LAST_PAGE = I18nMessage(key="lastPage", zh_cn="尾页", en_us="Last")
    PAGE_INFO = I18nMessage(
        key="pageInfo",
        zh_cn="第 {current} / {total} 页",
        en_us="Page {current} of {total}",
    )
    TOTAL_ROWS = I18nMessage(
        key="totalRows",
        zh_cn="共 {total} 条",
        en_us="Total {total}",
    )
    ROWS_PER_PAGE = I18nMessage(key="rowsPerPage", zh_cn="每页", en_us="Per page")
    JUMP_TO_PAGE = I18nMessage(key="jumpToPage", zh_cn="跳至", en_us="Go to")
    PAGE_SUFFIX = I18nMessage(key="pageSuffix", zh_cn="页", en_us="")

    # 数据状态
    NO_DATA = I18nMessage(key="noData", zh_cn="暂无数据", en_us="No data")
    EMPTY_DIR = I18nMessage(
        key="emptyDir",
        zh_cn="该目录为空或没有数据库文件",
        en_us="Directory is empty or has no database files",
    )
    INPUT_PATH = I18nMessage(
        key="inputPath", zh_cn="输入路径直接跳转...", en_us="Enter path to navigate..."
    )

    # 确认对话框
    CONFIRM_DELETE = I18nMessage(
        key="confirmDelete",
        zh_cn="确定要删除这条记录吗？",
        en_us="Are you sure you want to delete this record?",
    )

    # 错误消息
    INSERT_FAILED = I18nMessage(
        key="insertFailed", zh_cn="插入失败", en_us="Insert failed"
    )
    UPDATE_FAILED = I18nMessage(
        key="updateFailed", zh_cn="更新失败", en_us="Update failed"
    )
    DELETE_FAILED = I18nMessage(
        key="deleteFailed", zh_cn="删除失败", en_us="Delete failed"
    )
    RENAME_FAILED = I18nMessage(
        key="renameFailed", zh_cn="重命名失败", en_us="Rename failed"
    )
    SAVE_COMMENT_FAILED = I18nMessage(
        key="saveCommentFailed", zh_cn="更新备注失败", en_us="Failed to update comment"
    )
    NO_PK_CANNOT_EDIT = I18nMessage(
        key="noPkCannotEdit",
        zh_cn="该表没有主键，无法编辑数据",
        en_us="This table has no primary key, cannot edit data",
    )
    NO_PK_CANNOT_DELETE = I18nMessage(
        key="noPkCannotDelete",
        zh_cn="该表没有主键，无法删除",
        en_us="This table has no primary key, cannot delete",
    )
    NO_PK_CANNOT_SAVE = I18nMessage(
        key="noPkCannotSave",
        zh_cn="该表没有主键，无法保存",
        en_us="This table has no primary key, cannot save",
    )
    TABLE_NAME_REQUIRED = I18nMessage(
        key="tableNameRequired", zh_cn="表名不能为空", en_us="Table name is required"
    )
    DELETE_TABLE = I18nMessage(key="deleteTable", zh_cn="删除表", en_us="Delete Table")
    CONFIRM_DELETE_TABLE = I18nMessage(
        key="confirmDeleteTable",
        zh_cn=("确定要删除表 '{name}' 吗？此操作不可恢复，表中所有数据将被永久删除。"),
        en_us=(
            "Are you sure you want to delete table '{name}'? "
            "This action cannot be undone. "
            "All data in this table will be permanently deleted."
        ),
    )
    FIELD_REQUIRED = I18nMessage(
        key="fieldRequired", zh_cn="不能为空", en_us="is required"
    )

    # 列可见性
    COLUMNS_TOGGLE = I18nMessage(key="columnsToggle", zh_cn="列显示", en_us="Columns")

    # 侧边栏
    SEARCH_TABLE = I18nMessage(
        key="searchTable", zh_cn="搜索表名...", en_us="Search tables..."
    )
    COLLAPSE_SIDEBAR = I18nMessage(
        key="collapseSidebar", zh_cn="收起侧边栏", en_us="Collapse sidebar"
    )
    EXPAND_SIDEBAR = I18nMessage(
        key="expandSidebar", zh_cn="展开侧边栏", en_us="Expand sidebar"
    )


class ConvertUI(BaseUIClass):
    """引擎转换 UI 文本"""

    __i18n_prefix__ = "convert"

    CONVERT_ENGINE = I18nMessage(
        key="convertEngine", zh_cn="引擎转换", en_us="Convert Engine"
    )
    SOURCE_FILE = I18nMessage(key="sourceFile", zh_cn="源文件", en_us="Source File")
    TARGET_ENGINE = I18nMessage(
        key="targetEngine", zh_cn="目标引擎", en_us="Target Engine"
    )
    SAVE_PATH = I18nMessage(key="savePath", zh_cn="保存路径", en_us="Save Path")
    START_CONVERT = I18nMessage(
        key="startConvert", zh_cn="开始转换", en_us="Start Convert"
    )
    CONVERTING = I18nMessage(key="converting", zh_cn="转换中...", en_us="Converting...")
    SELECT_ENGINE = I18nMessage(
        key="selectEngine", zh_cn="请选择目标引擎", en_us="Select target engine"
    )
    CONVERT_SUCCESS = I18nMessage(
        key="convertSuccess",
        zh_cn="转换完成：{tables} 张表，{records} 条记录",
        en_us="Conversion completed: {tables} tables, {records} records",
    )
    CONVERT_FAILED = I18nMessage(
        key="convertFailed", zh_cn="转换失败", en_us="Conversion failed"
    )
