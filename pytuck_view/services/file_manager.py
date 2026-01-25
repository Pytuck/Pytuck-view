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
from typing import Any

from pytuck.backends import is_valid_pytuck_database

from pytuck_view.base.exceptions import ServiceException
from pytuck_view.base.i18n import FileI18n
from pytuck_view.base.schemas import FileRecord
from pytuck_view.utils.logger import logger
from pytuck_view.utils.tiny_func import simplify_exception


class FileManager:
    """文件管理器"""

    def __init__(self) -> None:
        # 配置文件存储在用户 home 目录下的 .pytuck-view 目录
        self.config_dir = Path.home() / ".pytuck-view"
        self.config_file: Path | None = self.config_dir / "recent_files.json"
        self.open_files: dict[str, FileRecord] = {}  # 当前打开的文件
        self.temporary_files: dict[
            str, str
        ] = {}  # file_id -> 临时文件路径（仅内存，用于 upload-open 清理）
        self._ensure_config_dir()

    def _ensure_config_dir(self) -> None:
        """确保配置目录存在"""
        try:
            self.config_dir.mkdir(exist_ok=True)
        except Exception as e:
            # 如果无法创建配置目录，使用内存存储
            logger.warning(
                "无法创建配置目录 %s, 将使用内存存储: %s",
                self.config_dir,
                simplify_exception(e),
            )
            self.config_file = None

    def _load_recent_files(self) -> list[FileRecord]:
        """从 JSON 文件加载最近文件列表"""
        if not self.config_file or not self.config_file.exists():
            return []

        try:
            with open(self.config_file, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    # 新格式：包含 files 和 last_browse_directory
                    files = data.get("files", [])
                    return [FileRecord(**item) for item in files]
                else:
                    return []
        except Exception as e:
            logger.warning("无法加载最近文件列表: %s", simplify_exception(e))
            return []

    def _save_recent_files(self, files: list[FileRecord]) -> None:
        """保存最近文件列表到 JSON 文件"""
        if not self.config_file:
            return  # 内存模式，不保存

        try:
            # 读取现有配置以保留 last_browse_directory
            existing_last_dir = None
            if self.config_file.exists():
                try:
                    with open(self.config_file, encoding="utf-8") as f:
                        existing_data = json.load(f)
                        if isinstance(existing_data, dict):
                            existing_last_dir = existing_data.get(
                                "last_browse_directory"
                            )
                except Exception:
                    pass

            # 新格式：包含 files 和 last_browse_directory
            data = {
                "last_browse_directory": existing_last_dir,
                "files": [record.model_dump() for record in files],
            }

            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("无法保存最近文件列表: %s", simplify_exception(e))

    def get_recent_files(self, limit: int = 10) -> list[FileRecord]:
        """获取最近打开的文件列表"""
        files = self._load_recent_files()
        # 按最后打开时间排序，最新的在前面
        files.sort(key=lambda x: x.last_opened, reverse=True)
        return files[:limit]

    def open_file(self, file_path: str) -> FileRecord | None:
        """打开文件并添加到历史记录"""
        path_obj = Path(file_path)

        # 检查文件是否存在
        if not path_obj.exists():
            raise ServiceException(FileI18n.FILE_NOT_FOUND, path=file_path)

        # 验证文件并识别引擎
        is_valid, engine = is_valid_pytuck_database(path_obj)
        if not is_valid:
            raise ServiceException(FileI18n.INVALID_DATABASE_FILE, path=str(path_obj))

        # 生成文件 ID 和记录
        file_id = str(uuid.uuid4())
        file_record = FileRecord(
            file_id=file_id,
            path=str(path_obj.absolute()),
            name=path_obj.stem,
            last_opened=datetime.now().isoformat(),
            file_size=path_obj.stat().st_size,
            engine_name=engine or "unknown",
        )

        # 添加到当前打开的文件
        self.open_files[file_id] = file_record

        # 更新历史记录
        self._add_to_history(file_record)

        return file_record

    def _add_to_history(self, file_record: FileRecord) -> None:
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

    def get_open_file(self, file_id: str) -> FileRecord | None:
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

    def close_file(self, file_id: str) -> None:
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
                logger.warning(
                    "无法删除临时文件 %s: %s", temp_path, simplify_exception(e)
                )

    def get_last_browse_directory(self) -> str | None:
        """获取最后浏览的目录"""
        if not self.config_file or not self.config_file.exists():
            return None

        try:
            with open(self.config_file, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data.get("last_browse_directory")
        except Exception:
            pass
        return None

    def update_last_browse_directory(self, directory: str) -> None:
        """更新最后浏览的目录"""
        if not self.config_file:
            return

        try:
            # 读取现有数据
            data: dict[str, Any] = {"files": []}
            if self.config_file.exists():
                with open(self.config_file, encoding="utf-8") as f:
                    existing_data = json.load(f)
                    if isinstance(existing_data, dict):
                        data = existing_data
                    elif isinstance(existing_data, list):
                        # 兼容旧格式
                        data = {"files": existing_data}

            # 更新 last_browse_directory
            data["last_browse_directory"] = directory

            # 保存
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("更新最后浏览目录失败: %s", simplify_exception(e))

    def discover_files(self, directory: str | None = None) -> list[dict[str, Any]]:
        """在指定目录中发现 pytuck 文件"""
        target_dir = Path.cwd() / "databases" if directory is None else Path(directory)

        if not target_dir.exists() or not target_dir.is_dir():
            return []

        discovered_files: list[dict[str, Any]] = []

        try:
            for file_path in target_dir.iterdir():
                if not file_path.is_file():
                    continue
                # 验证文件
                is_valid, engine = is_valid_pytuck_database(file_path)
                if not is_valid:
                    continue
                try:
                    size = file_path.stat().st_size
                    discovered_files.append(
                        {
                            "path": str(file_path.absolute()),
                            "name": file_path.stem,
                            "extension": file_path.suffix,
                            "size": size,
                        }
                    )
                except Exception as e:
                    logger.warning(
                        "无法读取文件信息 %s: %s", file_path, simplify_exception(e)
                    )
        except Exception as e:
            logger.warning("无法扫描目录 %s: %s", target_dir, simplify_exception(e))

        return discovered_files


# 全局文件管理器实例
file_manager = FileManager()
