#!/usr/bin/env python3
"""
pytuck-view 应用入口点

启动 uvicorn 服务器并自动打开浏览器
从固定端口 54540 开始，若占用则递增
"""

import sys
import threading
import time
import webbrowser
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from pytuck_view import __version__
from pytuck_view.utils.logger import init_logging, logger
from pytuck_view.utils.tiny_func import find_available_port, simplify_exception

# 默认起始端口
DEFAULT_PORT = 54540


def open_browser(url: str, delay: float = 1.5) -> None:
    """延迟打开浏览器，确保服务器已启动"""

    def _open() -> None:
        time.sleep(delay)
        try:
            webbrowser.open(url)
        except Exception as e:
            logger.warning(f"无法自动打开浏览器: {simplify_exception(e)}")
            logger.info(f"请手动访问: {url}")

    threading.Thread(target=_open, daemon=True).start()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理"""
    logger.info("🚀 pytuck-view 正在启动...")
    yield
    logger.info("👋 pytuck-view 正在关闭...")


def main() -> None:
    """主入口函数"""
    # 首先初始化日志系统
    init_logging()

    try:
        # 查找可用端口（从 54540 开始）
        port = find_available_port(DEFAULT_PORT)
        url = f"http://localhost:{port}"

        logger.info(f"📊 pytuck-view v{__version__}")
        logger.info(f"🌐 服务器启动在: {url}")
        logger.info("按 Ctrl+C 停止服务器")

        # 延迟打开浏览器
        open_browser(url)

        # 启动 uvicorn 服务器
        uvicorn.run(
            "pytuck_view.app:create_app",
            factory=True,
            host="127.0.0.1",
            port=port,
            access_log=False,  # 减少日志输出，保持简洁
            log_level="warning",  # 只显示警告和错误
        )

    except KeyboardInterrupt:
        logger.info("\n✨ 感谢使用 pytuck-view!")
    except Exception as e:
        logger.error(f"❌ 启动失败: {simplify_exception(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
