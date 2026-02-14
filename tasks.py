"""
pytuck-view 开发任务脚本

使用 invoke 提供跨平台的开发和构建命令。
自动检测环境：有 uv 时通过 uv run 执行，无 uv 时直接调用工具。
pip 用户请先安装对应的 requirements 文件：
    pip install -r requirements-dev.txt    # 开发依赖
    pip install -r requirements-build.txt  # 构建依赖

常用命令：
    invoke fmt          - 格式化代码
    invoke lint         - 代码检查
    invoke typecheck    - 类型检查
    invoke test         - 运行测试
    invoke check        - 运行所有检查
    invoke run          - 启动开发服务器
    invoke wheel        - 构建 wheel 包
    invoke zipapp       - 构建 zipapp
    invoke exe          - 构建独立可执行文件
    invoke clean        - 清理构建产物
"""

import shutil
from pathlib import Path

from invoke import task

# 检测 uv 是否可用，决定命令执行方式
_USE_UV = shutil.which("uv") is not None


def _cmd(cmd: str, group: str | None = None) -> str:
    """根据环境构造命令：有 uv 时走 uv run，无 uv 时直接执行。"""
    if _USE_UV:
        prefix = f"uv run --group {group}" if group else "uv run"
        return f"{prefix} {cmd}"
    return cmd


@task
def fmt(c):
    """格式化代码"""
    print("正在格式化代码...")
    c.run(_cmd("ruff format .", group="dev"))
    print("代码格式化完成")


@task
def lint(c):
    """代码检查"""
    print("正在运行代码检查...")
    c.run(_cmd("ruff check .", group="dev"))


@task
def typecheck(c):
    """类型检查"""
    print("正在运行类型检查...")
    c.run(_cmd("mypy pytuck_view", group="dev"))


@task
def test(c):
    """运行测试"""
    print("正在运行测试...")
    c.run(_cmd("pytest -q", group="dev"))


@task
def check(c):
    """运行所有检查（lint + typecheck + test）"""
    print("正在运行所有检查...\n")
    print("[1/3] 代码检查...")
    lint(c)
    print("\n[2/3] 类型检查...")
    typecheck(c)
    print("\n[3/3] 运行测试...")
    test(c)
    print("\n✓ 所有检查通过！")


@task
def run(c):
    """启动开发服务器"""
    print("正在启动开发服务器...")
    c.run(_cmd("uvicorn pytuck_view.app:create_app --factory --reload --port 54540"))


@task
def wheel(c):
    """构建 wheel 包"""
    print("正在构建 wheel 包...")
    c.run(_cmd("python -m build --wheel", group="build"))
    print("\n✓ wheel 包已生成到 dist/ 目录")


@task
def build(c):
    """构建 wheel 包（别名）"""
    wheel(c)


@task
def zipapp(c):
    """构建 zipapp（.pyz 单文件）"""
    print("正在构建 zipapp（.pyz）...")
    Path("dist").mkdir(exist_ok=True)
    zipapp_cmd = (
        'python -m zipapp pytuck_view -o dist/pytuck-view.pyz -p "/usr/bin/env python3"'
    )
    cmd = _cmd(zipapp_cmd, group="build")
    c.run(cmd)
    print("\n✓ zipapp 已生成到 dist/pytuck-view.pyz")


@task
def exe(c):
    """构建独立可执行文件（.exe）"""
    print("正在使用 nuitka 构建独立可执行文件...")
    print("注意：这可能需要几分钟时间...\n")
    c.run(
        _cmd(
            "python -m nuitka "
            "--onefile "
            "--output-dir=dist "
            "--output-filename=pytuck-view.exe "
            "pytuck_view/__main__.py",
            group="build",
        )
    )
    print("\n✓ 可执行文件已生成到 dist/pytuck-view.exe")


@task
def clean(c):
    """清理构建产物"""
    print("正在清理构建产物...")

    # 清理构建目录
    dirs_to_remove = ["dist", "build", "pytuck_view.egg-info"]
    for d in dirs_to_remove:
        path = Path(d)
        if path.exists():
            print(f"  删除 {d}/")
            shutil.rmtree(path)

    # 清理 __pycache__
    pycache_count = 0
    for pycache in Path(".").rglob("__pycache__"):
        shutil.rmtree(pycache)
        pycache_count += 1

    # 清理 .pyc 文件
    pyc_count = 0
    for pyc in Path(".").rglob("*.pyc"):
        pyc.unlink()
        pyc_count += 1

    print(f"  清理了 {pycache_count} 个 __pycache__ 目录")
    print(f"  清理了 {pyc_count} 个 .pyc 文件")
    print("\n✓ 清理完成")
