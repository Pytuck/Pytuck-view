# pytuck-view 使用指南

## 项目简介

pytuck-view 是 pytuck 的轻量级数据浏览器，提供一个"一眼看完"的 Web 界面来查看本地数据库。

**核心特性**：
- 🚀 零配置、双击即跑
- 📦 单文件打包（zipapp ≤ 2 MB，exe ≤ 8 MB）
- 🔒 纯本地运行，不联网、无账号
- 🎯 简洁界面，快速浏览表结构和数据

**项目地址**：
- github: [https://github.com/go9sky/pytuck-view](https://github.com/go9sky/pytuck-view)
- gitee: [https://gitee.com/go9sky/pytuck-view](https://gitee.com/go9sky/pytuck-view)

## 快速开始

### 安装方式

#### 方式 1：使用 PyPI（推荐）
```bash
pip install pytuck-view
```

#### 方式 2：从源码安装
```bash
git clone https://github.com/go9sky/pytuck-view.git
cd pytuck-view
pip install -e .
```

### 启动应用
```bash
# 方式 1：直接运行（已安装）
pytuck-view

# 方式 2：作为模块运行
python -m pytuck_view
```

应用会自动：
- 选择一个可用端口（如 8000）
- 启动 FastAPI 服务器
- 打开默认浏览器访问应用

## 开发指南

### 环境准备

本项目使用 `uv` 进行依赖管理，确保已安装 Python 3.12+。

```bash
# 克隆项目
git clone https://github.com/go9sky/pytuck-view.git
cd pytuck-view

# 安装 uv（如果尚未安装）
pip install uv

# 同步开发环境（包含 dev 依赖组）
uv sync --group dev --group build
```

### 运行开发服务器

```bash
# 方式 1：使用 invoke（推荐）
invoke run

# 方式 2：直接使用 uvicorn
uv run uvicorn pytuck_view.app:create_app --factory --reload --port 8000
```

### 代码质量检查

```bash
# 使用 invoke（推荐）
invoke fmt          # 格式化代码
invoke check        # 运行所有检查（lint + typecheck + test）
invoke lint         # 单独运行 lint
invoke typecheck    # 单独运行类型检查
invoke test         # 单独运行测试

# 或直接使用 uv run 命令
uv run --group dev ruff format .
uv run --group dev ruff check .
uv run --group dev mypy pytuck_view
uv run --group dev pytest -q
```

### 打包发布

#### 构建 wheel 包（用于 PyPI）

```bash
# 使用 invoke（推荐）
invoke wheel
# 或
invoke build

# 或直接使用命令
uv run --group build python -m build --wheel
```

构建完成后，可以上传到 PyPI：
```bash
# 安装 twine
pip install twine

# 上传到 PyPI
twine upload dist/pytuck_view-*.whl

# 或上传到 TestPyPI（测试用）
twine upload --repository testpypi dist/pytuck-view-*.whl
```

#### 构建 zipapp（跨平台单文件）

```bash
# 使用 invoke
invoke zipapp

# 或直接使用命令
uv run --group build python -m zipapp pytuck_view -o dist/pytuck-view.pyz -p "/usr/bin/env python3"
```

#### 构建独立可执行文件

```bash
# 使用 invoke
invoke exe

# 或直接使用命令
uv run --group build python -m nuitka --onefile --output-dir=dist --output-filename=pytuck-view.exe pytuck_view/__main__.py
```

#### 清理构建产物

```bash
# 使用 invoke
invoke clean
```

## 功能说明

#### 1. 文件选择界面
- **选择文件**：点击"选择文件"按钮（在 Web 环境中会提示使用文件扫描）
- **扫描当前目录**：自动发现当前目录下的 .bin、.json、.csv 文件
- **最近打开**：显示最近使用过的数据库文件

#### 2. 数据库浏览界面
- **表列表**：左侧边栏显示数据库中的所有表
- **表结构**：显示选中表的列信息和数据类型
- **数据查看**：分页显示表中的数据
- **排序功能**：点击列标题进行升序/降序排序
- **分页导航**：支持首页、上一页、下一页、尾页

## API 端点

- `GET /`：主界面
- `GET /health`：健康检查
- `GET /api/recent-files`：获取最近文件
- `GET /api/discover-files`：发现当前目录文件
- `POST /api/open-file`：打开数据库文件
- `GET /api/tables/{file_id}`：获取表列表
- `GET /api/schema/{file_id}/{table}`：获取表结构
- `GET /api/rows/{file_id}/{table}`：获取表数据
- `GET /api/status`：服务状态

## 支持的文件格式

- 不限格式，pytuck 数据库文件皆可

## 系统要求

- Python 3.12+
- 现代浏览器（Chrome 70+, Firefox 63+, Edge 79+）
- 依赖包：fastapi, uvicorn, pydantic, pytuck

## 注意事项

1. **只读模式**：当前版本仅支持数据查看，不支持数据编辑
2. **文件历史**：应用会在当前目录的 `.pytuck-view/recent_files.json` 中存储最近打开的文件历史
3. **随机端口**：应用使用随机可用端口，启动时会显示具体地址
4. **体积优化**：整个 wheel 包 ≤ 2 MB，独立 exe ≤ 10 MB

## 故障排除

如果遇到问题：

1. 确保所有依赖已安装：`uv sync`
2. 检查 Python 版本：`python --version`（需要 3.12+）
3. 查看控制台错误信息
4. 确认数据库文件格式正确

## 技术栈

- **后端**：FastAPI + uvicorn
- **前端**：Vue 3（单文件版本） + 原生 CSS
- **打包**：build (wheel) + zipapp + nuitka (exe)
- **代码质量**：ruff (formatter + linter) + mypy (strict) + pytest

## 开发信息

- 版本：0.1.1
- Python 要求：≥ 3.12
- 许可：跟随 pytuck 项目
- 代码行数：约 1200 行
- 静态资源：< 200KB

## 贡献指南

欢迎提交 Issue 和 Pull Request！提交 PR 前请确保：

1. 运行 `make check` 通过所有检查
2. 添加必要的测试
3. 更新相关文档
4. 保持代码简洁，避免过度工程

## 相关链接

- [pytuck 主项目](https://github.com/go9sky/pytuck)
- [问题反馈](https://github.com/go9sky/pytuck-view/issues)
- [更新日志](CHANGELOG.md)