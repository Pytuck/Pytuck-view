# pytuck-view / Claude-Code 开发手册

## 项目一句话
给 pytuck 本地数据库一个“一眼看完”的轻量浏览器界面——零配置、零依赖（安装级零感知）、双击即跑。

## 核心定位
- **附属小工具**：生命周期随用随关，不抢 pytuck 核心风头。
- **纯本地**：不联网、无账号、不存储配置、不留日志。
- **单文件可携**：zipapp ≤ 2 MB，nuitka --onefile ≤ 8 MB。
- **前后端一体**：单进程、随机端口、自动开浏览器；代码层面路由与静态分层，未来可秒拆远程。

## 技术选型（冻结）
| 组件 | 选型 | 版本锁定 | 理由 |
|---|---|---|---|
| 后端 | FastAPI | `>=0.128,<1` | 开发快、异步预留、纯 Python |
| 服务器 | uvicorn | `>=0.20` | 同样纯 Python，Windows 无编译 |
| 前端 | vue.min.js | 3.x 单文件落盘 | 体积小、响应式、与"view"谐音 |
| UI 框架 | 无 | 原生 HTML + 少量 CSS | 避免打包体积爆炸 |
| 代码风格 | ruff | formatter + linter（统一入口） | 提交前 `invoke fmt` |
| 类型检查 | mypy | strict（CI 门禁） | 关键边界类型覆盖，降低回归风险 |
| 最低 Python | 3.12+ | 与 pyproject.toml 一致 | 使用 3.12 typing 改进 |

**注意**：项目已移除 Jinja2 模板引擎，前端改为纯静态 HTML + Vue 3，后端仅提供 JSON API。

## 目录规范
```
pytuck_view/
 ├─ __main__.py         # 唯一入口：uvicorn.run + 浏览器自启
 ├─ app.py              # FastAPI 工厂，挂 static、路由
 ├─ api/
 │   ├─ __init__.py
 │   ├─ files.py        # 文件管理相关端点
 │   └─ tables.py       # 表/数据相关端点
 ├─ static/             # 纯静态资源
 │   ├─ index.html      # 主页面（纯静态，无模板语法）
 │   ├─ vue.min.js      # Vue 3 本地文件
 │   └─ app.css         # 样式文件
 ├─ services/           # 业务逻辑层
 ├─ base/               # 基础模块（schemas、middleware 等）
 ├─ utils/              # 工具函数
 └─ tests/              # 用 pytest，不依赖外部服务
```
> 新增文件先问自己：用户需要多下载多少 KB？> 50 KB 需写理由。

## 运行/调试

**重要提示**：本项目使用虚拟环境管理依赖，开发者使用 invoke 作为跨平台任务运行器。

### 环境准备
```bash
# 激活虚拟环境（如果尚未激活）
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# 或使用 uv sync 同步依赖
uv sync --group dev --group build
```

### 开发运行
```bash
# 方式1：使用 invoke（推荐）
invoke run

# 方式2：直接使用 uvicorn
uv run uvicorn pytuck_view.app:create_app --factory --reload --port 8000
```

### 本地质量门禁（建议提交前运行；CI 会强制）
```bash
invoke fmt      # ruff format
invoke check    # ruff check + mypy(strict) + pytest
```

### 一键打包
```bash
invoke wheel   # 生成 wheel 包到 dist/
invoke zipapp  # 生成 dist/pytuck-view.pyz
invoke exe     # nuitka --onefile，生成 dist/pytuck-view.exe
```

## API 设计原则
1. 只暴露“读 + 点改”：  
   `GET  /api/tables` → 列表  
   `GET  /api/rows/{table}` → 分页数据  
   `POST /api/row/{table}/{pk}` → 单行编辑（事务短）
2. 所有接口 JSON，状态码遵守 HTTP 语义。
3. 出错时 `{"detail": "人类可读原因"}`，前端直接 `alert(detail)`。

## 前端约定
- 不使用模板引擎，`static/index.html` 为纯静态 HTML 文件。
- 不写 `.vue` 单文件，直接在 `index.html` 内嵌 `<script>`，减少构建链。
- 静态资源路径全部 `/static/...`，方便以后 CDN 替换。
- 样式直接写在 `<style>` 标签中，总 CSS ≤ 20 KB。
- 网络请求封装成 `async function api(path, options)`，统一错误处理。
- 使用 Vue 3 响应式 API（`reactive`、`computed` 等）管理状态。

## 体积红线
- 整个 wheel ≤ 2 MB；
- 独立 exe ≤ 10 MB；
- PR 若增加 > 100 KB，CI 自动贴体积 diff 并 require review。

补充说明：
- ruff/mypy/pytest 属于 dev-only 工具，不应进入运行时依赖与打包产物体积核算；但 CI 与本地开发必须执行它们作为质量门禁。
- 新增运行时依赖或新增/扩大 vendor、static 内容 > 50 KB，必须在 PR 描述写明理由与体积影响。

## 兼容性承诺
- 支持 pytuck 最新两个小版本；
- 浏览器支持 Chromium 70+（Win10 自带 Edge）、Firefox 63+；
- 不依赖浏览器插件、不依赖 ES2020 以后语法。

## 发布流程
1. 版本号使用 `major.minor.patch` 语义，`patch` 递增。
2. tag 即发布：git push origin 0.1.0 → GitHub Action 自动 build wheel / exe → PyPI。
3. 写 Release Notes ≤ 3 行：新增、修复、体积变化。

## 禁止清单
- ❌ 不引入新的 C 扩展、不依赖系统库。
- ❌ 不在用户目录写配置/缓存（除非一次性临时文件，退出即删）。
- ❌ 不在前端调用外部 CDN（vue.min.js 必须随包）。
- ❌ 不增加账号、登录、权限、多语言、主题切换等任何"可配置"功能。
- ❌ 不在主包 import 时执行耗时逻辑（连 DB 等），延迟到首次请求。
- ❌ 不将 ruff/mypy/pytest 等 dev-only 工具作为运行时依赖（不得进入 wheel/exe 的依赖链）。
- ❌ 不在运行时自动触发静态检查（ruff/mypy）或写入任何日志文件（调试输出仅限显式开启）。

## 国际化要求（硬性）
- **前端 UI 文本必须国际化**：所有用户可见文本必须通过 i18n 系统处理。语言切换本身除外。
- **禁止硬编码文本**：不得在 HTML 中直接写任何用户可见的中文或英文文本。
- **统一使用 `t('key')` 函数**：所有前端显示文本通过 `{{ t('key') }}` 或 `t('key')` 调用。
- **新增 UI 文本必须添加翻译**：在 `pytuck_view/base/frontend_i18n.py` 中添加对应的 `I18nMessage`。
- **翻译类组织规范**：
  - `CommonUI`：通用文本（按钮、状态等）
  - `FileUI`：文件操作相关
  - `TableUI`：表格/数据相关
  - `DataEditUI`：数据编辑相关
  - `ErrorUI`：错误消息
- **后端日志使用 f-string**：禁止使用 `%s` 格式化，统一使用 f-string（Python 3.12+ 规范）。

## Claude-Code 助手要求
- **始终使用中文回答**：与用户的所有交互、代码注释、文档说明均使用中文。
- **技术术语适度保留英文**：如 FastAPI、JSON、HTTP、Vue.js 等可保持英文，但解释说明用中文。
- **代码注释中文化**：Python 代码中的注释、文档字符串使用中文编写。

## Python 3.12+ 通用开发规范（项目版）

本章是 `python3.12项目开发通用规范.md` 的项目落地子集：在**不增加运行时复杂度与体积**的前提下，提高类型安全、边界清晰与可维护性。

### MUST（强制）
1. **单向依赖，禁止循环引用**：底层模块不得反向 import API/app 层。
2. **结构化数据**：API 输入/输出必须使用 Pydantic 模型表达；禁止在业务逻辑中传播“裸 dict”。
3. **类型门禁**：CI 必须通过 `mypy --strict`（以项目配置为准）。
4. **风格门禁**：CI 必须通过 `ruff format` 与 `ruff check`。
5. **Pathlib 统一**：新增代码禁止使用 `os.path` 拼接。
6. **异常边界**：内部抛项目异常，API 层统一转换为 `{"detail": "人类可读原因"}`。

### SHOULD（建议）
1. 公共契约（异常、类型别名、schema 基类）集中在公共模块，避免散落。
2. 测试使用 pytest，必须离线可跑，不依赖外部服务。

### MAY（可选）
1. 对特别复杂的结构可做 DTO/Schema 分层（内部 DTO 与 API Schema 分离）。

## 一句话自检
每次 commit 前问自己：
**"用户能不能 `pip install pytuck-view` 后 5 秒内看到表数据？"**
如果不能，回炉。