"""
数据库服务层

提供 pytuck Storage 的统一接口
处理数据库连接、表查询、模式信息等
对于缺失的功能提供占位符和警告信息
"""

import ctypes
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from pytuck import Column, Session, Storage
from pytuck.backends import is_valid_pytuck_database
from pytuck.common.exceptions import DuplicateKeyError, SchemaError as PytuckSchemaError
from pytuck.common.options import CsvBackendOptions, JsonBackendOptions
from pytuck.core.storage import Table

from pytuck_view.base.exceptions import ServiceException
from pytuck_view.base.i18n import DatabaseI18n, FileI18n
from pytuck_view.utils.logger import logger
from pytuck_view.utils.tiny_func import simplify_exception


@dataclass
class TableInfo:
    """表信息数据类"""

    name: str
    row_count: int
    columns: list[dict[str, Any]]
    comment: str | None = None


@dataclass
class ColumnInfo:
    """列信息数据类"""

    name: str
    type: str
    nullable: bool
    primary_key: bool


# ========== 列提取辅助函数 ==========


def _extract_column_from_object(col_name: str, col_obj: Column) -> dict[str, Any]:
    """从列对象中提取列信息（字典格式的列定义）"""
    col_type_str = (
        col_obj.col_type.__name__
        if isinstance(col_obj.col_type, type)
        else str(col_obj.col_type)
    )
    return {
        "name": str(col_name),
        "type": col_type_str,
        "nullable": col_obj.nullable,
        "primary_key": col_obj.primary_key,
        "default_value": str(col_obj.default) if col_obj.default is not None else None,
        "comment": str(col_obj.comment) if col_obj.comment else None,
        # Column 没有 autoincrement/unique 属性，保留 getattr 兼容
        "autoincrement": bool(getattr(col_obj, "autoincrement", False)),
        "unique": bool(getattr(col_obj, "unique", False)),
    }


def _extract_column_from_dict(col_def: dict[str, Any]) -> dict[str, Any]:
    """从字典中提取列信息（数组格式的列定义）"""
    return {
        "name": str(col_def.get("name", "unknown")),
        "type": str(col_def.get("type", "unknown")),
        "nullable": bool(col_def.get("nullable", True)),
        "primary_key": bool(col_def.get("primary_key", False)),
        "default_value": (
            str(col_def.get("default")) if col_def.get("default") is not None else None
        ),
        "comment": (
            str(col_def.get("comment", "")) if col_def.get("comment") else None
        ),
        "autoincrement": bool(col_def.get("autoincrement", False)),
        "unique": bool(col_def.get("unique", False)),
    }


def _extract_columns_from_table(table: Table) -> list[dict[str, Any]]:
    """从表对象中提取所有列信息"""
    columns: list[dict[str, Any]] = []

    if not hasattr(table, "columns") or not table.columns:
        return columns

    if isinstance(table.columns, dict):
        # 字典格式的列定义
        for col_name, col_obj in table.columns.items():
            columns.append(_extract_column_from_object(col_name, col_obj))
    elif isinstance(table.columns, list):
        # 数组格式的列定义（pytuck JSON 格式）
        for col_def in table.columns:
            if isinstance(col_def, dict):
                columns.append(_extract_column_from_dict(col_def))

    return columns


# ========== 列类型映射 ==========

_COLUMN_TYPE_MAP: dict[str, type] = {
    "int": int,
    "float": float,
    "str": str,
    "bool": bool,
    "list": list,
    "dict": dict,
    "bytes": bytes,
    "datetime": datetime,
    "date": date,
    "timedelta": timedelta,
}


def _build_columns_from_defs(columns_def: list[dict[str, Any]]) -> list[Column]:
    """将列定义字典列表转换为 Column 对象列表

    Args:
        columns_def: 列定义列表，每个元素包含 name、col_type、nullable 等

    Returns:
        Column 对象列表
    """
    columns: list[Column] = []
    for col_def in columns_def:
        col_type_str = col_def.get("col_type", "str")
        col_type = _COLUMN_TYPE_MAP.get(col_type_str, str)
        col = Column(
            col_type,
            name=col_def.get("name"),
            nullable=col_def.get("nullable", True),
            primary_key=col_def.get("primary_key", False),
            default=col_def.get("default"),
            comment=col_def.get("comment"),
        )
        columns.append(col)
    return columns


def _get_row_count_from_table(
    table: Table, storage: Storage | None, table_name: str
) -> int:
    """从表对象中获取行数"""
    # 优先使用 storage.count_rows（推荐方式）
    if storage is not None and hasattr(storage, "count_rows"):
        try:
            return storage.count_rows(table_name)
        except Exception:
            pass

    # 后备方案：从 table 对象直接获取（兼容旧版本）
    if hasattr(table, "data") and table.data:
        return len(table.data)

    return 0


def _extract_table_comment(table: Table) -> str | None:
    """提取表备注"""
    try:
        if hasattr(table, "comment"):
            return str(table.comment) if table.comment else None
        elif isinstance(table, dict) and "comment" in table:
            return str(table["comment"]) if table["comment"] else None
    except Exception:
        pass
    return None


# ========== 过滤器操作符处理 ==========


_FILTER_OPERATORS: dict[str, Callable[[Any, Any], bool]] = {
    "eq": lambda row_val, val: row_val == val,
    "gt": lambda row_val, val: float(row_val or 0) > float(val or 0),
    "gte": lambda row_val, val: float(row_val or 0) >= float(val or 0),
    "lt": lambda row_val, val: float(row_val or 0) < float(val or 0),
    "lte": lambda row_val, val: float(row_val or 0) <= float(val or 0),
    "contains": lambda row_val, val: str(val).lower() in str(row_val).lower(),
    "in": lambda row_val, val: (
        row_val in val if isinstance(val, list) else row_val == val
    ),
}


def _apply_filter_operator(op: str, row_value: Any, value: Any) -> bool:
    """应用单个过滤器操作符"""
    handler = _FILTER_OPERATORS.get(op)
    if handler:
        try:
            return bool(handler(row_value, value))
        except (ValueError, TypeError):
            return False
    return True  # 未知操作符，不过滤


def _row_matches_filters(row: dict[str, Any], filters: list[dict[str, Any]]) -> bool:
    """检查单行是否匹配所有过滤条件"""
    for filter_def in filters:
        field = filter_def.get("field")
        op = filter_def.get("op", "eq")
        value = filter_def.get("value")

        if field not in row:
            return False

        if not _apply_filter_operator(op, row[field], value):
            return False

    return True


# ========== 占位符数据 ==========


def _get_placeholder_tables() -> list[str]:
    """返回占位符表列表（当 pytuck 功能不可用时）"""
    return [
        "⚠️ 表列表功能暂不可用",
        "💡 提示: 需要在 pytuck 库中添加获取表列表的方法",
        "📋 建议方法: storage.list_tables() 或 storage.get_table_names()",
    ]


def _get_placeholder_columns() -> list[dict[str, Any]]:
    """返回占位符列信息"""
    return [
        {
            "name": "⚠️ 列信息不可用",
            "type": "placeholder",
            "nullable": True,
            "primary_key": False,
            "description": "需要在 pytuck 库中添加获取表结构的方法",
        }
    ]


def _get_placeholder_data() -> list[dict[str, Any]]:
    """返回占位符数据"""
    return [
        {
            "id": 1,
            "message": "⚠️ 数据查询功能暂不可用",
            "suggestion": "需要在 pytuck 库中完善数据查询接口",
            "methods_needed": "storage.query() 或 session.execute(select())",
            "is_placeholder": True,
        }
    ]


# ========== 数据库服务类 ==========


class DatabaseService:
    """数据库服务"""

    def __init__(self) -> None:
        self.storage: Storage | None = None
        self.session: Session | None = None
        self.file_path: str | None = None

    def open_database(self, file_path: str) -> bool:
        """打开数据库文件"""
        try:
            path_obj = Path(file_path)
            if not path_obj.exists():
                raise ServiceException(FileI18n.FILE_NOT_FOUND, path=file_path)

            # 验证文件并识别引擎
            is_valid, engine = is_valid_pytuck_database(path_obj)
            if not is_valid:
                raise ServiceException(
                    FileI18n.INVALID_DATABASE_FILE, path=str(path_obj)
                )

            opts: CsvBackendOptions | JsonBackendOptions | None = None
            match engine:
                case "csv":
                    # csv.field_size_limit() 接受 C long，Windows 上为 32 位
                    # ctypes.sizeof(ctypes.c_long) 获取平台 C long 字节数
                    _max_c_long = 2 ** (8 * ctypes.sizeof(ctypes.c_long) - 1) - 1
                    opts = CsvBackendOptions(field_size_limit=_max_c_long)
                case "json":
                    opts = JsonBackendOptions(impl="orjson")
                case _:
                    opts = None

            # 创建 Storage 实例
            self.storage = Storage(
                file_path=str(path_obj),
                engine=engine or "binary",
                auto_flush=False,  # 只读模式，不需要自动刷新
                backend_options=opts,
            )

            # 创建 Session 实例
            self.session = Session(self.storage)
            self.file_path = file_path

            return True

        except Exception as e:
            logger.error(f"打开数据库失败: {simplify_exception(e)}")
            return False

    def list_tables(self) -> list[str]:
        """列出所有表名"""
        if not self.storage:
            raise RuntimeError("数据库未打开")

        try:
            # 尝试获取表列表
            if hasattr(self.storage, "tables"):
                return [str(name) for name in self.storage.tables.keys()]
            else:
                # 如果 pytuck 还没有提供表列表功能，返回占位符
                return _get_placeholder_tables()

        except Exception as e:
            logger.error(f"获取表列表失败: {simplify_exception(e)}")
            return _get_placeholder_tables()

    def get_table_info(self, table_name: str) -> TableInfo | None:
        """获取表信息（模式和行数）"""
        if not self.storage:
            raise RuntimeError("数据库未打开")

        # 如果是占位符表名，返回占位符信息
        if table_name.startswith(("⚠️", "💡", "📋")):
            return TableInfo(
                name=table_name,
                row_count=0,
                columns=[
                    {
                        "name": "message",
                        "type": "str",
                        "nullable": False,
                        "primary_key": False,
                        "description": "这是一个提示信息：该功能需要在 pytuck 库中实现",
                    }
                ],
            )

        try:
            # 尝试获取表对象
            if hasattr(self.storage, "get_table"):
                table: Table = self.storage.get_table(table_name)
                if table:
                    return self._extract_table_info(table, table_name)

            # 如果获取失败，返回占位符信息
            return self._get_placeholder_table_info(table_name)

        except Exception as e:
            logger.error(f"获取表信息失败 {table_name}: {simplify_exception(e)}")
            return self._get_placeholder_table_info(table_name)

    def _extract_table_info(self, table: Table, table_name: str) -> TableInfo:
        """从 pytuck 表对象提取信息"""
        try:
            columns = _extract_columns_from_table(table)
            row_count = _get_row_count_from_table(table, self.storage, table_name)
        except Exception as e:
            logger.error(f"提取表信息失败: {simplify_exception(e)}")
            columns = []
            row_count = 0

        table_comment = _extract_table_comment(table)

        return TableInfo(
            name=table_name,
            row_count=row_count,
            columns=columns if columns else _get_placeholder_columns(),
            comment=table_comment,
        )

    def _get_placeholder_table_info(self, table_name: str) -> TableInfo:
        """返回占位符表信息"""
        return TableInfo(
            name=table_name, row_count=0, columns=_get_placeholder_columns()
        )

    def get_table_data(
        self,
        table_name: str,
        page: int = 1,
        limit: int = 50,
        sort_by: str | None = None,
        order: str = "asc",
        filters: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """获取表数据（支持服务端分页和过滤）"""
        if not isinstance(self.storage, Storage):
            raise RuntimeError("数据库未打开")

        try:
            result = self._query_table_data(
                table_name, page, limit, sort_by, order, filters
            )
            rows, total = self._parse_query_result(result)
            serialized_rows = [self._serialize_value(row) for row in rows]

            logger.debug(
                f"使用服务端分页查询 {table_name}，"
                f"返回 {len(serialized_rows)} 行，总计 {total} 行"
            )

            return {
                "rows": serialized_rows,
                "total": total,
                "page": page,
                "limit": limit,
                "server_side": True,
            }

        except Exception as e:
            logger.error(f"获取表数据失败 {table_name}: {simplify_exception(e)}")
            return {
                "rows": _get_placeholder_data(),
                "total": 1,
                "page": page,
                "limit": limit,
                "server_side": False,
            }

    def _query_table_data(
        self,
        table_name: str,
        page: int,
        limit: int,
        sort_by: str | None,
        order: str,
        filters: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        """执行表数据查询"""
        if not isinstance(self.storage, Storage):
            raise RuntimeError("数据库未打开")

        offset = (page - 1) * limit
        order_desc = order.lower() == "desc"

        # 将 filters 转换为 pytuck 期望的格式
        filters_dict: dict[str, Any] | None = None
        if filters:
            filters_dict = {
                f.get("field", ""): f.get("value") for f in filters if f.get("field")
            }

        return self.storage.query_table_data(
            table_name=table_name,
            limit=limit,
            offset=offset,
            order_by=sort_by,
            order_desc=order_desc,
            filters=filters_dict,
        )

    def _parse_query_result(self, result: dict[str, Any]) -> tuple[list[Any], int]:
        """解析查询结果，返回 (rows, total)"""
        rows: list[Any] = []
        total: int = 0

        rows = list(result.get("records", result.get("rows", [])) or [])
        total_val = result.get("total_count", result.get("total", len(rows)))
        total = int(total_val) if total_val is not None else 0

        return rows, total

    def _serialize_value(self, value: Any) -> Any:
        """将值序列化为 JSON 兼容格式"""
        if value is None:
            return None
        elif isinstance(value, (str, int, float, bool)):
            return value
        elif isinstance(value, type):
            # 处理类型对象，如 <class 'int'>
            return value.__name__
        elif isinstance(value, (list, tuple)):
            return [self._serialize_value(item) for item in value]
        elif isinstance(value, dict):
            return {
                k: self._serialize_value(v) for k, v in value.items() if not callable(v)
            }
        elif hasattr(value, "__dict__"):
            # 对象转字典
            return {
                k: self._serialize_value(v)
                for k, v in value.__dict__.items()
                if not k.startswith("_") and not callable(v)
            }
        else:
            # 其他类型转字符串
            try:
                return str(value)
            except Exception:
                return "unknown"

    def _apply_filters(
        self, rows: list[dict[str, Any]], filters: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """在内存中应用过滤条件"""
        if not filters or not rows:
            return rows

        return [row for row in rows if _row_matches_filters(row, filters)]

    def supports_server_side_pagination(self) -> bool:
        """检测 storage 或 storage.backend 是否支持服务器端分页"""
        if not isinstance(self.storage, Storage):
            return False
        if self.storage.backend is None:
            return False
        return bool(self.storage.backend.supports_server_side_pagination())

    def get_capabilities(self) -> dict[str, Any]:
        """获取数据库后端的能力信息"""
        if not self.storage:
            return {
                "server_side_pagination": False,
                "supports_filters": False,
                "backend_name": "unknown",
                "status": "not_connected",
            }

        try:
            return {
                "server_side_pagination": self.supports_server_side_pagination(),
                "supports_filters": hasattr(self.storage, "query_table_data"),
                "backend_name": self.storage.engine_name,
                "status": "connected",
            }
        except Exception as e:
            return {
                "server_side_pagination": False,
                "supports_filters": False,
                "backend_name": "unknown",
                "status": "error",
                "error": str(e),
            }

    def close(self) -> None:
        """关闭数据库连接"""
        if self.session:
            try:
                # pytuck Session 可能没有显式的 close 方法
                # 只需要清理引用
                self.session = None
            except Exception:
                pass

        self.storage = None
        self.file_path = None

    def get_database_info(self) -> dict[str, Any]:
        """获取数据库基本信息"""
        if not self.storage:
            return {"error": "数据库未打开"}

        try:
            tables = self.list_tables()
            # 过滤掉占位符表名
            real_tables = [t for t in tables if not t.startswith(("⚠️", "💡", "📋"))]

            # 获取能力信息
            capabilities = self.get_capabilities()

            return {
                "file_path": self.file_path,
                "file_size": os.path.getsize(self.file_path) if self.file_path else 0,
                "tables_count": len(real_tables),
                "engine": self.storage.engine_name,
                "status": "connected",
                "capabilities": capabilities,
            }
        except Exception as e:
            return {"error": f"获取数据库信息失败: {e}", "status": "error"}

    # ========== Schema 修改操作 ==========

    def get_primary_key_column(self, table_name: str) -> str | None:
        """获取表的主键列名

        无用户定义主键时返回 '_pytuck_rowid'（pytuck 隐式行号）作为后备。

        Args:
            table_name: 表名

        Returns:
            主键列名，或 '_pytuck_rowid'（隐式行号）
        """
        if not self.storage:
            raise RuntimeError("数据库未打开")

        try:
            table = self.storage.get_table(table_name)
            # 有用户定义主键直接返回，否则用 pytuck 隐式行号兜底
            return table.primary_key or "_pytuck_rowid"
        except Exception as e:
            logger.error(f"获取主键列失败 {table_name}: {simplify_exception(e)}")
            return None

    def has_user_primary_key(self, table_name: str) -> bool:
        """检查表是否有用户定义的主键（非隐式 _pytuck_rowid）

        Args:
            table_name: 表名

        Returns:
            True 表示有用户定义的主键，False 表示使用隐式行号
        """
        if not self.storage:
            raise RuntimeError("数据库未打开")

        try:
            table = self.storage.get_table(table_name)
            return table.primary_key is not None
        except Exception as e:
            logger.error(f"获取主键信息失败 {table_name}: {simplify_exception(e)}")
            return False

    def rename_table(self, old_name: str, new_name: str) -> None:
        """重命名表

        Args:
            old_name: 原表名
            new_name: 新表名

        Raises:
            RuntimeError: 数据库未打开
            ServiceException: 重命名失败
        """
        if not self.storage:
            raise RuntimeError("数据库未打开")

        try:
            self.storage.rename_table(old_name, new_name)
            self.storage.flush()
        except Exception as e:
            logger.error(
                f"重命名表失败 {old_name} -> {new_name}: {simplify_exception(e)}"
            )
            raise ServiceException(
                DatabaseI18n.RENAME_TABLE_FAILED,
                error=simplify_exception(e),
            ) from e

    def update_table_comment(self, table_name: str, comment: str | None) -> None:
        """更新表备注

        Args:
            table_name: 表名
            comment: 新备注（None 表示清空）

        Raises:
            RuntimeError: 数据库未打开
            ServiceException: 更新失败
        """
        if not self.storage:
            raise RuntimeError("数据库未打开")

        try:
            self.storage.update_table_comment(table_name, comment)
            self.storage.flush()
        except Exception as e:
            logger.error(f"更新表备注失败 {table_name}: {simplify_exception(e)}")
            raise ServiceException(
                DatabaseI18n.UPDATE_COMMENT_FAILED,
                error=simplify_exception(e),
            ) from e

    def update_column_comment(
        self, table_name: str, column_name: str, comment: str | None
    ) -> None:
        """更新列备注

        Args:
            table_name: 表名
            column_name: 列名
            comment: 新备注（None 表示清空）

        Raises:
            RuntimeError: 数据库未打开
            ServiceException: 更新失败
        """
        if not self.storage:
            raise RuntimeError("数据库未打开")

        try:
            self.storage.update_column(table_name, column_name, comment=comment)
            self.storage.flush()
        except Exception as e:
            logger.error(
                f"更新列备注失败 {table_name}.{column_name}: {simplify_exception(e)}"
            )
            raise ServiceException(
                DatabaseI18n.UPDATE_COMMENT_FAILED,
                error=simplify_exception(e),
            ) from e

    # ========== 数据行操作 ==========

    def insert_row(self, table_name: str, data: dict[str, Any]) -> Any:
        """插入一行数据

        Args:
            table_name: 表名
            data: 行数据

        Returns:
            插入的主键值

        Raises:
            RuntimeError: 数据库未打开
            ServiceException: 插入失败或主键重复
        """
        if not self.storage:
            raise RuntimeError("数据库未打开")

        try:
            pk = self.storage.insert(table_name, data)
            self.storage.flush()
            return pk
        except DuplicateKeyError as e:
            logger.warning(f"主键重复 {table_name}: {e.pk}")
            raise ServiceException(
                DatabaseI18n.DUPLICATE_KEY,
                pk=str(e.pk),
            ) from e
        except Exception as e:
            logger.error(f"插入数据失败 {table_name}: {simplify_exception(e)}")
            raise ServiceException(
                DatabaseI18n.INSERT_FAILED,
                error=simplify_exception(e),
            ) from e

    def update_row(self, table_name: str, pk: Any, data: dict[str, Any]) -> None:
        """更新一行数据

        Args:
            table_name: 表名
            pk: 主键值
            data: 要更新的数据

        Raises:
            RuntimeError: 数据库未打开
            ServiceException: 更新失败或表没有主键
        """
        if not self.storage:
            raise RuntimeError("数据库未打开")

        # 检查表是否有主键
        pk_col = self.get_primary_key_column(table_name)
        if pk_col is None:
            raise ServiceException(DatabaseI18n.NO_PRIMARY_KEY)

        try:
            self.storage.update(table_name, pk, data)
            self.storage.flush()
        except Exception as e:
            logger.error(f"更新数据失败 {table_name}[{pk}]: {simplify_exception(e)}")
            raise ServiceException(
                DatabaseI18n.UPDATE_FAILED,
                error=simplify_exception(e),
            ) from e

    def delete_row(self, table_name: str, pk: Any) -> None:
        """删除一行数据

        Args:
            table_name: 表名
            pk: 主键值

        Raises:
            RuntimeError: 数据库未打开
            ServiceException: 删除失败或表没有主键
        """
        if not self.storage:
            raise RuntimeError("数据库未打开")

        # 检查表是否有主键
        pk_col = self.get_primary_key_column(table_name)
        if pk_col is None:
            raise ServiceException(DatabaseI18n.NO_PRIMARY_KEY)

        try:
            self.storage.delete(table_name, pk)
            self.storage.flush()
        except Exception as e:
            logger.error(f"删除数据失败 {table_name}[{pk}]: {simplify_exception(e)}")
            raise ServiceException(
                DatabaseI18n.DELETE_FAILED,
                error=simplify_exception(e),
            ) from e

    def drop_table(self, table_name: str) -> None:
        """删除整张表（包含所有数据）

        Args:
            table_name: 表名

        Raises:
            RuntimeError: 数据库未打开
            ServiceException: 删除失败
        """
        if not self.storage:
            raise RuntimeError("数据库未打开")

        try:
            self.storage.drop_table(table_name)
            self.storage.flush()
        except Exception as e:
            logger.error(f"删除表失败 {table_name}: {simplify_exception(e)}")
            raise ServiceException(
                DatabaseI18n.DROP_TABLE_FAILED,
                error=simplify_exception(e),
            ) from e

    def clear_table(self, table_name: str) -> int:
        """清空表数据（保留表结构）

        通过 drop + create 策略实现，保留原有的列定义和表备注。

        Args:
            table_name: 表名

        Returns:
            被清空的行数

        Raises:
            RuntimeError: 数据库未打开
            ServiceException: 清空失败
        """
        if not self.storage:
            raise RuntimeError("数据库未打开")

        try:
            table = self.storage.get_table(table_name)
            # 保存表结构信息
            columns = list(table.columns.values())
            comment = table.comment if hasattr(table, "comment") else None
            row_count = _get_row_count_from_table(table, self.storage, table_name)

            # drop + create 重建空表
            self.storage.drop_table(table_name)
            self.storage.create_table(table_name, columns, comment)
            self.storage.flush()

            return row_count
        except Exception as e:
            logger.error(f"清空表失败 {table_name}: {simplify_exception(e)}")
            raise ServiceException(
                DatabaseI18n.CLEAR_TABLE_FAILED,
                error=simplify_exception(e),
            ) from e

    def create_table(
        self,
        table_name: str,
        columns_def: list[dict[str, Any]],
        comment: str | None = None,
    ) -> int:
        """创建新表

        Args:
            table_name: 表名
            columns_def: 列定义列表，每个元素包含 name、col_type、nullable 等
            comment: 表备注

        Returns:
            创建的列数

        Raises:
            RuntimeError: 数据库未打开
            ServiceException: 创建失败或表已存在
        """
        if not self.storage:
            raise RuntimeError("数据库未打开")

        # 检查表是否已存在
        if table_name in self.storage.tables:
            raise ServiceException(
                DatabaseI18n.TABLE_ALREADY_EXISTS,
                table_name=table_name,
            )

        try:
            columns = _build_columns_from_defs(columns_def)
            self.storage.create_table(table_name, columns, comment)
            self.storage.flush()
            return len(columns)
        except ServiceException:
            raise
        except Exception as e:
            logger.error(f"创建表失败 {table_name}: {simplify_exception(e)}")
            raise ServiceException(
                DatabaseI18n.CREATE_TABLE_FAILED,
                error=simplify_exception(e),
            ) from e

    def add_column(
        self,
        table_name: str,
        column_def: dict[str, Any],
        default_value: Any = None,
    ) -> None:
        """向表添加列

        Args:
            table_name: 表名
            column_def: 列定义字典
            default_value: 为现有记录填充的默认值

        Raises:
            RuntimeError: 数据库未打开
            ServiceException: 添加失败
        """
        if not self.storage:
            raise RuntimeError("数据库未打开")

        try:
            columns = _build_columns_from_defs([column_def])
            column = columns[0]
            self.storage.add_column(table_name, column, default_value)
            self.storage.flush()
        except PytuckSchemaError as e:
            logger.warning(
                f"添加列 Schema 错误 {table_name}.{column_def.get('name')}: "
                f"{simplify_exception(e)}"
            )
            raise ServiceException(
                DatabaseI18n.ADD_COLUMN_SCHEMA_ERROR,
                error=simplify_exception(e),
            ) from e
        except Exception as e:
            logger.error(
                f"添加列失败 {table_name}.{column_def.get('name')}: "
                f"{simplify_exception(e)}"
            )
            raise ServiceException(
                DatabaseI18n.ADD_COLUMN_FAILED,
                error=simplify_exception(e),
            ) from e

    def drop_column(self, table_name: str, column_name: str) -> None:
        """从表中删除列

        Args:
            table_name: 表名
            column_name: 列名

        Raises:
            RuntimeError: 数据库未打开
            ServiceException: 删除失败
        """
        if not self.storage:
            raise RuntimeError("数据库未打开")

        try:
            self.storage.drop_column(table_name, column_name)
            self.storage.flush()
        except Exception as e:
            logger.error(
                f"删除列失败 {table_name}.{column_name}: {simplify_exception(e)}"
            )
            raise ServiceException(
                DatabaseI18n.DROP_COLUMN_FAILED,
                error=simplify_exception(e),
            ) from e
