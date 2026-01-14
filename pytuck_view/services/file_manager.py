"""
文件管理服务

管理最近打开的文件历史记录
使用轻量级 JSON 存储，存储在程序同级目录
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pytuck.backends import is_valid_pytuck_database

from pytuck_view.common.logger import get_logger
from pytuck_view.common.tiny_func import simplify_exception


@dataclass
class FileRecord:
    """文件记录数据类"""
    file_id: str
    path: str
    name: str
    last_opened: str
    file_size: int
    engine_name: str


class FileManager:
    """文件管理器"""

    def __init__(self):
        # 配置文件存储在程序入口同级的 .pytuck-view 目录下
        self.config_dir = Path.cwd() / ".pytuck-view"
        self.config_file = self.config_dir / "recent_files.json"
        self.open_files: Dict[str, FileRecord] = {}  # 当前打开的文件
        self.temporary_files: Dict[str, str] = {}  # file_id -> 临时文件路径（仅内存，用于 upload-open 清理）
        self._ensure_config_dir()

    def _ensure_config_dir(self):
        """确保配置目录存在"""
        try:
            self.config_dir.mkdir(exist_ok=True)
        except Exception as e:
            # 如果无法创建配置目录，使用内存存储
            logger = get_logger(__name__)
            logger.warning("无法创建配置目录 %s, 将使用内存存储: %s", self.config_dir, simplify_exception(e))
            self.config_file = None

    def _load_recent_files(self) -> List[FileRecord]:
        """从 JSON 文件加载最近文件列表"""
        if not self.config_file or not self.config_file.exists():
            return []

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [FileRecord(**item) for item in data]
        except Exception as e:
            logger = get_logger(__name__)
            logger.warning("无法加载最近文件列表: %s", simplify_exception(e))
            return []

    def _save_recent_files(self, files: List[FileRecord]):
        """保存最近文件列表到 JSON 文件"""
        if not self.config_file:
            return  # 内存模式，不保存

        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                data = [asdict(record) for record in files]
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger = get_logger(__name__)
            logger.warning("无法保存最近文件列表: %s", simplify_exception(e))

    def get_recent_files(self, limit: int = 10) -> List[FileRecord]:
        """获取最近打开的文件列表"""
        files = self._load_recent_files()
        # 按最后打开时间排序，最新的在前面
        files.sort(key=lambda x: x.last_opened, reverse=True)
        return files[:limit]

    def open_file(self, file_path: str) -> Optional[FileRecord]:
        """打开文件并添加到历史记录"""
        path_obj = Path(file_path)

        # 检查文件是否存在
        if not path_obj.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 检查是否为支持的 pytuck 文件格式
        is_valid, engine = is_valid_pytuck_database(path_obj)
        if not is_valid:
            raise ValueError(f"该文件并非 Pytuck 数据库文件: {path_obj}")

        # 生成文件 ID 和记录
        file_id = str(uuid.uuid4())
        file_record = FileRecord(
            file_id=file_id,
            path=str(path_obj.absolute()),
            name=path_obj.stem,
            last_opened=datetime.now().isoformat(),
            file_size=path_obj.stat().st_size,
            engine_name=engine
        )

        # 添加到当前打开的文件
        self.open_files[file_id] = file_record

        # 更新历史记录
        self._add_to_history(file_record)

        return file_record

    def _add_to_history(self, file_record: FileRecord):
        """将文件记录添加到历史记录"""
        files = self._load_recent_files()

        # 移除相同路径的旧记录
        files = [f for f in files if f.path != file_record.path]

        # 添加新记录到开头
        files.insert(0, file_record)

        # 保持最多 20 个历史记录
        files = files[:20]

        # 保存更新后的列表
        self._save_recent_files(files)

    def get_open_file(self, file_id: str) -> Optional[FileRecord]:
        """根据 file_id 获取当前打开的文件信息"""
        return self.open_files.get(file_id)

    def remove_from_history(self, file_id: str) -> bool:
        """从历史记录中移除指定 file_id。

        仅删除 recent_files.json 中的记录，不会删除用户原始文件。
        临时上传文件的清理由 close_file/temporary_files 负责。
        """
        files = self._load_recent_files()
        new_files = [f for f in files if f.file_id != file_id]
        if len(new_files) == len(files):
            return False

        self._save_recent_files(new_files)
        return True

    def close_file(self, file_id: str):
        """关闭文件"""
        self.open_files.pop(file_id, None)

        # 如果是 upload-open 产生的临时文件，关闭时顺手清理
        temp_path = self.temporary_files.pop(file_id, None)
        if temp_path:
            try:
                try:
                    os.remove(temp_path)
                except FileNotFoundError:
                    pass
            except Exception as e:
                logger = get_logger(__name__)
                logger.warning("无法删除临时文件 %s: %s", temp_path, simplify_exception(e))

    def discover_files(self, directory: Optional[str] = None) -> List[Dict]:
        """在指定目录中发现 pytuck 文件"""
        target_dir = Path.cwd() / 'databases' if directory is None else Path(directory)

        if not target_dir.exists() or not target_dir.is_dir():
            return []

        discovered_files = []

        try:
            for file_path in target_dir.iterdir():
                if not file_path.is_file(): continue
                is_valid, engine = is_valid_pytuck_database(file_path)
                if not is_valid: continue
                try:
                    size = file_path.stat().st_size
                    discovered_files.append({
                        "path": str(file_path.absolute()),
                        "name": file_path.stem,
                        "extension": file_path.suffix,
                        "size": size
                    })
                except Exception as e:
                    logger = get_logger(__name__)
                    logger.warning("无法读取文件信息 %s: %s", file_path, simplify_exception(e))
        except Exception as e:
            logger = get_logger(__name__)
            logger.warning("无法扫描目录 %s: %s", target_dir, simplify_exception(e))

        return discovered_files


# 全局文件管理器实例
file_manager = FileManager()