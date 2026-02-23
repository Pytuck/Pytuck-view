"""
FastAPI 应用工厂

创建和配置 FastAPI 应用实例
挂载静态文件和路由
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .api import router as api_router
from .base.middleware import language_context_middleware


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用"""

    # 在应用启动时生成前端翻译文件
    from pytuck_view import __version__
    from pytuck_view.base.setup import setup_all

    setup_all()

    app = FastAPI(
        title="pytuck-view",
        description="轻量级 pytuck 数据库可视化工具",
        version=__version__,
        docs_url=None,  # 禁用自动文档以减小体积
        redoc_url=None,
    )

    # 获取当前目录路径
    current_dir = Path(__file__).parent

    # 挂载静态文件
    static_path = current_dir / "static"
    if static_path.exists():
        app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

    # 中间件：注入请求上下文（language）
    app.middleware("http")(language_context_middleware)

    # 注册 API 路由
    app.include_router(api_router, prefix="/api")

    # 根路径路由 - 返回静态主页面
    static_index = current_dir / "static" / "index.html"

    @app.get("/", response_class=FileResponse, response_model=None)
    async def home() -> FileResponse | HTMLResponse:
        """返回静态主页面"""
        if static_index.exists():
            return FileResponse(str(static_index))
        else:
            # 如果静态文件不存在，返回简单的 HTML
            return HTMLResponse("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>pytuck-view</title>
                <meta charset="utf-8">
            </head>
            <body>
                <h1>pytuck-view</h1>
                <p>index.html 未找到。</p>
            </body>
            </html>
            """)

    # 健康检查端点
    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """健康检查端点"""
        return {"status": "ok", "service": "pytuck-view"}

    return app
