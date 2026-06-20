# APILLM Frontend — 前端展示站

基于纯 HTML / CSS / Vanilla JS 的 APILLM Relay 前端 Dashboard。

## 文件结构

```
Web/
├── index.html       # 主页面
├── css/
│   └── style.css    # 样式表（暗色极简 + 响应式）
├── js/
│   ├── api.js       # API 客户端（fetch 封装、认证、流式 SSE）
│   └── app.js       # 应用逻辑（健康轮询、模型加载、Chat Playground）
└── README.md
```

## 功能

- **系统健康** — 实时显示 Redis / DB 状态，每 30s 自动轮询
- **模型列表** — 加载上游所有可用模型，点击即可在 Playground 使用
- **API Playground** — 在线测试 Chat Completions，支持流式 (SSE) 和非流式
- **快速开始** — 展示 Python SDK 和 curl 调用示例

## 使用方式

### 方式一：直接打开（需处理后端 CORS）

1. 确保后端 API 已在 `http://127.0.0.1:8000` 运行
2. 浏览器打开 `Web/index.html`
3. 在导航栏输入 API Key，点击"应用"
4. 健康状态自动加载，点击"刷新模型"获取可用模型列表
5. 在 Playground 中发送消息测试

### 方式二：由 FastAPI 托管静态文件（推荐）

在 `app/main.py` 中挂载静态目录：

```python
from fastapi.staticfiles import StaticFiles

app.mount("/", StaticFiles(directory="Web", html=True), name="web")
```

之后访问 `http://127.0.0.1:8000` 即可。

### 方式三：使用任意静态文件服务器

```bash
# Python
python -m http.server 3000 -d Web

# Node.js
npx serve Web

# VS Code Live Server
# 右键 index.html → Open with Live Server
```

## API 对接说明

前端默认连接 `http://127.0.0.1:8000`：

- `GET /health` — 健康检查（无需认证）
- `GET /v1/models` — 模型列表（需要 Bearer Token）
- `POST /v1/chat/completions` — Chat Completions（需要 Bearer Token，支持 streaming）

API Key 格式：`sk-relay-{raw_key}`，与后端 `create_user.py` 生成的 Key 一致。

## 浏览器兼容

- Chrome 90+
- Firefox 90+
- Safari 15+
- Edge 90+

需要支持 `ReadableStream`（SSE 流式读取）。
