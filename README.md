# pytuck-view 使用指南

## 快速开始

### 启动应用
```bash
cd E:\projects\my\Pytuck-view
python -m pytuck_view
```

应用会自动：
- 选择一个可用端口（如 8000）
- 启动 FastAPI 服务器
- 打开默认浏览器访问应用

### 功能说明

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

### API 端点

- `GET /`：主界面
- `GET /health`：健康检查
- `GET /api/recent-files`：获取最近文件
- `GET /api/discover-files`：发现当前目录文件
- `POST /api/open-file`：打开数据库文件
- `GET /api/tables/{file_id}`：获取表列表
- `GET /api/schema/{file_id}/{table}`：获取表结构
- `GET /api/rows/{file_id}/{table}`：获取表数据
- `GET /api/status`：服务状态

### 支持的文件格式

- `.bin`：pytuck 二进制格式
- `.json`：JSON 格式数据库
- `.csv`：CSV 格式数据库

### 系统要求

- Python 3.12+
- 现代浏览器（Chrome 70+, Firefox 63+, Edge 79+）
- 依赖包：fastapi, uvicorn, jinja2, pydantic, pytuck

### 注意事项

1. **占位符功能**：部分功能依赖于 pytuck 库的完整实现，如果看到警告提示，表示需要在 pytuck 库中添加相应支持。

2. **文件历史**：应用会在当前目录的 `.pytuck-view/recent_files.json` 中存储最近打开的文件历史。

3. **只读模式**：当前版本仅支持数据查看，不支持数据编辑。

4. **端口**：应用使用随机可用端口，启动时会显示具体地址。

### 故障排除

如果遇到问题：

1. 确保所有依赖已安装：`uv sync`
2. 检查 Python 版本：`python --version`（需要 3.12+）
3. 查看控制台错误信息
4. 确认数据库文件格式正确

## 开发信息

- 版本：0.1.0
- 作者：pytuck-view
- 许可：跟随 pytuck 项目
- 代码行数：约 1200 行
- 静态资源：< 200KB