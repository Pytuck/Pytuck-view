"""
日志配置模块
- 零依赖：只使用 Python 标准库 logging
- 零配置：内置默认配置，不创建配置文件
- 不留日志：只输出到控制台，绝不写入磁盘文件
- 保持简洁：默认输出简洁，通过环境变量开启详细模式
"""

import logging
import os
import sys

DEFAULT_LEVEL = logging.INFO
DEBUG_ENV = "PYTUCK_VIEW_DEBUG"


def init_logging(verbosity: int | None = None) -> None:
    """
    初始化全局 logging 配置。应在程序入口尽早调用（例如 __main__）。

    Args:
        verbosity: None = 使用环境变量或默认；>0 表示启用调试模式
    """
    if verbosity is None:
        verbosity = 1 if os.environ.get(DEBUG_ENV) in ("1", "true", "True") else 0

    root = logging.getLogger()

    # 删除已有 handlers（防止重复配置）
    if root.handlers:
        for h in list(root.handlers):
            root.removeHandler(h)

    if verbosity:
        level = logging.DEBUG
        fmt = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
        datefmt = "%Y-%m-%d %H:%M:%S"
    else:
        level = DEFAULT_LEVEL
        fmt = "%(levelname)s: %(message)s"
        datefmt = None

    root.setLevel(level)
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setLevel(level)
    formatter = logging.Formatter(fmt, datefmt=datefmt)
    handler.setFormatter(formatter)
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的 logger"""
    return logging.getLogger(name)


# 导出全局 logger 实例，供所有模块使用
# 使用包名作为 logger 名称，统一日志来源
logger = get_logger("pytuck_view")
