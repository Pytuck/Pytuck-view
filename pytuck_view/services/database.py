"""
数据库服务层

提供 pytuck Storage 的统一接口
处理数据库连接、表查询、模式信息等
对于缺失的功能提供占位符和警告信息
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pytuck import Storage, Session
from pytuck.backends import is_valid_pytuck_database

from pytuck_view.common.tiny_func import simplify_exception
from pytuck_view.common.logger import get_logger


@dataclass
class TableInfo:
    """表信息数据类"""
    name: str
    row_count: int
    columns: List[Dict[str, Any]]


@dataclass
class ColumnInfo:
    """列信息数据类"""
    name: str
    type: str
    nullable: bool
    primary_key: bool


class DatabaseService:
    """数据库服务"""

    def __init__(self):
        self.storage: Optional[Storage] = None
        self.session: Optional[Session] = None
        self.file_path: Optional[str] = None

    def open_database(self, file_path: str) -> bool:
        """打开数据库文件"""
        try:
            path_obj = Path(file_path)
            if not path_obj.exists():
                raise FileNotFoundError(f"数据库文件不存在: {file_path}")

            # 根据文件扩展名确定引擎类型
            is_valid, engine = is_valid_pytuck_database(file_path)

            # 创建 Storage 实例
            self.storage = Storage(
                file_path=str(path_obj),
                engine=engine,
                auto_flush=False  # 只读模式，不需要自动刷新
            )

            # 创建 Session 实例
            self.session = Session(self.storage)
            self.file_path = file_path

            return True

        except Exception as e:
            logger = get_logger(__name__)
            logger.error("打开数据库失败: %s", simplify_exception(e))
            return False

    def list_tables(self) -> List[str]:
        """列出所有表名"""
        if not self.storage:
            raise RuntimeError("数据库未打开")

        try:
            # 尝试获取表列表
            if hasattr(self.storage, 'tables'):
                table_names = []
                for table_name in self.storage.tables.keys():
                    table_names.append(str(table_name))  # 确保是字符串
                return table_names
            else:
                # 如果 pytuck 还没有提供表列表功能，返回占位符
                return self._get_placeholder_tables()

        except Exception as e:
            logger = get_logger(__name__)
            logger.error("获取表列表失败: %s", simplify_exception(e))
            return self._get_placeholder_tables()

    def _get_placeholder_tables(self) -> List[str]:
        """返回占位符表列表（当 pytuck 功能不可用时）"""
        return [
            "⚠️ 表列表功能暂不可用",
            "💡 提示: 需要在 pytuck 库中添加获取表列表的方法",
            "📋 建议方法: storage.list_tables() 或 storage.get_table_names()"
        ]

    def get_table_info(self, table_name: str) -> Optional[TableInfo]:
        """获取表信息（模式和行数）"""
        if not self.storage:
            raise RuntimeError("数据库未打开")

        # 如果是占位符表名，返回占位符信息
        if table_name.startswith(('⚠️', '💡', '📋')):
            return TableInfo(
                name=table_name,
                row_count=0,
                columns=[{
                    "name": "message",
                    "type": "str",
                    "nullable": False,
                    "primary_key": False,
                    "description": "这是一个提示信息，表示该功能需要在 pytuck 库中实现"
                }]
            )

        try:
            # 尝试获取表对象
            if hasattr(self.storage, 'get_table'):
                table = self.storage.get_table(table_name)
                if table:
                    return self._extract_table_info(table, table_name)

            # 如果获取失败，返回占位符信息
            return self._get_placeholder_table_info(table_name)

        except Exception as e:
            logger = get_logger(__name__)
            logger.error("获取表信息失败 %s: %s", table_name, simplify_exception(e))
            return self._get_placeholder_table_info(table_name)

    def _extract_table_info(self, table, table_name: str) -> TableInfo:
        """从 pytuck 表对象提取信息"""
        columns = []

        try:
            # 尝试获取列信息
            if hasattr(table, 'columns') and table.columns:
                # 处理不同的列格式
                if isinstance(table.columns, dict):
                    # 字典格式的列定义
                    for col_name, col_obj in table.columns.items():
                        col_info = {
                            "name": str(col_name),
                            "type": str(getattr(col_obj, 'col_type', getattr(col_obj, 'type', 'unknown'))),
                            "nullable": bool(getattr(col_obj, 'nullable', True)),
                            "primary_key": bool(getattr(col_obj, 'primary_key', False))
                        }
                        columns.append(col_info)
                elif isinstance(table.columns, list):
                    # 数组格式的列定义（pytuck JSON 格式）
                    for col_def in table.columns:
                        if isinstance(col_def, dict):
                            col_info = {
                                "name": str(col_def.get('name', 'unknown')),
                                "type": str(col_def.get('type', 'unknown')),
                                "nullable": bool(col_def.get('nullable', True)),
                                "primary_key": bool(col_def.get('primary_key', False))
                            }
                            columns.append(col_info)

            # 尝试获取行数
            row_count = 0
            if hasattr(table, 'records') and table.records:
                # pytuck JSON 格式使用 records
                row_count = len(table.records)
            elif hasattr(table, 'data') and table.data:
                # 其他格式使用 data
                row_count = len(table.data)
            elif hasattr(self.storage, 'count_rows'):
                # 假设将来会有这个方法
                try:
                    row_count = self.storage.count_rows(table_name)
                except:
                    row_count = 0

        except Exception as e:
            logger = get_logger(__name__)
            logger.error("提取表信息失败: %s", simplify_exception(e))
            columns = []
            row_count = 0

        return TableInfo(
            name=table_name,
            row_count=row_count,
            columns=columns if columns else self._get_placeholder_columns()
        )

    def _get_placeholder_table_info(self, table_name: str) -> TableInfo:
        """返回占位符表信息"""
        return TableInfo(
            name=table_name,
            row_count=0,
            columns=self._get_placeholder_columns()
        )

    def _get_placeholder_columns(self) -> List[Dict[str, Any]]:
        """返回占位符列信息"""
        return [{
            "name": "⚠️ 列信息不可用",
            "type": "placeholder",
            "nullable": True,
            "primary_key": False,
            "description": "需要在 pytuck 库中添加获取表结构的方法"
        }]

    def get_table_data(self, table_name: str, page: int = 1, limit: int = 50,
                       sort_by: Optional[str] = None, order: str = 'asc',
                       filters: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """获取表数据（支持服务端分页和过滤）"""
        if not isinstance(self.storage, Storage):
            raise RuntimeError("数据库未打开")

        try:
            # 计算偏移量
            offset = (page - 1) * limit
            server_side = False

            # 尝试调用 storage.query_table_data
            order_desc = order.lower() == 'desc'
            result = self.storage.query_table_data(
                table_name=table_name,
                limit=limit,
                offset=offset,
                order_by=sort_by,
                order_desc=order_desc,
                filters=filters
            )

            # 解析返回结果
            rows = []
            total = 0
            if isinstance(result, tuple) and len(result) >= 2:
                # 返回 (rows, total) 格式
                rows, total = result[:2]
            elif isinstance(result, dict):
                # 返回字典格式
                rows = result.get('records', result.get('rows', []))
                total = result.get('total_count', result.get('total', len(rows)))
            else:
                # 其他情况，假设返回行列表
                rows = list(result) if result else []
                total = len(rows)

            # 序列化数据（添加防护检查）
            serialized_rows = []

            # 防护：确保 rows 不为 None
            if rows is None:
                rows = []

            for row in rows:
                serialized_rows.append(self._serialize_value(row))

            server_side = True
            logger = get_logger(__name__)
            logger.debug("使用服务端分页查询 %s，返回 %d 行，总计 %d 行", table_name, len(serialized_rows), total)

            return {
                "rows": serialized_rows,
                "total": total,
                "page": page,
                "limit": limit,
                "server_side": True
            }

        except Exception as e:
            logger = get_logger(__name__)
            logger.error("获取表数据失败 %s: %s", table_name, simplify_exception(e))
            return {
                "rows": self._get_placeholder_data(),
                "total": 1,
                "page": page,
                "limit": limit,
                "server_side": False
            }

    def _serialize_value(self, value) -> Any:
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
            return {k: self._serialize_value(v) for k, v in value.items() if not callable(v)}
        elif hasattr(value, '__dict__'):
            # 对象转字典
            return {k: self._serialize_value(v) for k, v in value.__dict__.items()
                   if not k.startswith('_') and not callable(v)}
        else:
            # 其他类型转字符串
            try:
                return str(value)
            except:
                return "unknown"

    def _apply_filters(self, rows: List[Dict[str, Any]], filters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """在内存中应用过滤条件"""
        if not filters or not rows:
            return rows

        filtered_rows = []
        for row in rows:
            matches = True
            for filter_def in filters:
                field = filter_def.get('field')
                op = filter_def.get('op', 'eq')
                value = filter_def.get('value')

                if field not in row:
                    matches = False
                    break

                row_value = row[field]
                try:
                    if op == 'eq':
                        matches = row_value == value
                    elif op == 'gt':
                        matches = float(row_value) > float(value)
                    elif op == 'gte':
                        matches = float(row_value) >= float(value)
                    elif op == 'lt':
                        matches = float(row_value) < float(value)
                    elif op == 'lte':
                        matches = float(row_value) <= float(value)
                    elif op == 'contains':
                        matches = str(value).lower() in str(row_value).lower()
                    elif op == 'in':
                        matches = row_value in value if isinstance(value, list) else row_value == value
                    else:
                        matches = True  # 未知操作符，不过滤
                except (ValueError, TypeError):
                    matches = False  # 类型转换失败，视为不匹配

                if not matches:
                    break

            if matches:
                filtered_rows.append(row)

        return filtered_rows

    def _get_placeholder_data(self) -> List[Dict[str, Any]]:
        """返回占位符数据"""
        return [{
            "id": 1,
            "message": "⚠️ 数据查询功能暂不可用",
            "suggestion": "需要在 pytuck 库中完善数据查询接口",
            "methods_needed": "storage.query() 或 session.execute(select())",
            "is_placeholder": True
        }]

    def supports_server_side_pagination(self) -> bool:
        """检测 storage 或 storage.backend 是否支持服务器端分页"""
        if not isinstance(self.storage, Storage):
            return False
        return self.storage.backend.supports_server_side_pagination()

    def get_capabilities(self) -> Dict[str, Any]:
        """获取数据库后端的能力信息"""
        if not self.storage:
            return {
                "server_side_pagination": False,
                "supports_filters": False,
                "backend_name": "unknown",
                "status": "not_connected"
            }

        try:
            return {
                "server_side_pagination": self.supports_server_side_pagination(),
                "supports_filters": hasattr(self.storage, 'query_table_data'),
                "backend_name": getattr(self.storage, 'engine', 'unknown'),
                "status": "connected"
            }
        except Exception as e:
            return {
                "server_side_pagination": False,
                "supports_filters": False,
                "backend_name": "unknown",
                "status": "error",
                "error": str(e)
            }

    def close(self):
        """关闭数据库连接"""
        if self.session:
            try:
                # pytuck Session 可能没有显式的 close 方法
                # 只需要清理引用
                self.session = None
            except:
                pass

        self.storage = None
        self.file_path = None

    def get_database_info(self) -> Dict[str, Any]:
        """获取数据库基本信息"""
        if not self.storage:
            return {"error": "数据库未打开"}

        try:
            tables = self.list_tables()
            # 过滤掉占位符表名
            real_tables = [t for t in tables if not t.startswith(('⚠️', '💡', '📋'))]

            # 获取能力信息
            capabilities = self.get_capabilities()

            return {
                "file_path": self.file_path,
                "file_size": os.path.getsize(self.file_path) if self.file_path else 0,
                "tables_count": len(real_tables),
                "engine": getattr(self.storage, 'engine', 'unknown'),
                "status": "connected",
                "capabilities": capabilities
            }
        except Exception as e:
            return {
                "error": f"获取数据库信息失败: {e}",
                "status": "error"
            }