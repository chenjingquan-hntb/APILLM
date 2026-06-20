# Progress Log

## Session 1 — 基础架构搭建
- 创建项目骨架：pyproject.toml, .env, alembic 配置
- 实现 core/config, exceptions, logging
- 实现 db/models (User, ApiKey, Upstream), repositories
- 实现 schemas/openai, schemas/anthropic (含协议转换函数)
- 实现 services/auth (SHA-256 key 验证), services/router (priority 选择)
- 实现 services/proxy/openai (含非流式+流式)
- 实现 services/proxy/anthropic (含请求转换+流式 SSE 转换)
- 实现 api/v1/chat, api/v1/models, api/health
- 启动 PostgreSQL Docker 容器，运行 alembic 迁移
- 调试修复：MissingGreenlet → selectinload
- 调试修复：流式 HTTPException → ProxyError 分层
- 调试修复：ResponseNotRead → 改用 status_code
- 6/6 冒烟测试全部通过
- Git 仓库初始化并推送

## Session 2 — 代码质量优化 (/simplify)
- 三 agent 并行审查：代码复用、质量、效率
- 整合 httpx 客户端、提取 _url/_raise_for_http_error 到 base
- 并发聚合 list_models、移除冗余过滤
- 修复流式错误断连（ProxyError 替代 HTTPException）
- 第二轮 /simplify：统一错误格式、消除 URL 重复、router 兜底、model_validate_json

## Session 3 — 项目管理
- 创建 task_plan.md, findings.md, progress.md
- 确定 Phase 2 待实现：价格监控、智能路由、健康检测、故障切换

## Session 4 — 前端展示站开发
- UI/UX Pro Max 设计系统：暗色极简 × 夸张排版，参考 MiMo (mimo.xiaomi.com)
- 创建 design-system/apillm-relay/MASTER.md（全局设计规范）
- 创建 design-system/apillm-relay/pages/landing.md（落地页详细设计）
- 实现 Web/ 前端 Dashboard（纯 HTML/CSS/JS，零框架依赖）：
  - `index.html` — MiMo 风格 Hero 文字矩阵 + 健康状态 + 模型列表 + Chat Playground + Quick Start
  - `css/style.css` — 暗色 OLED 配色、4 层视差文字动画、响应式布局、reduced-motion 适配
  - `js/api.js` — fetch 封装：Bearer 认证、SSE 流式解析、错误处理、localStorage 持久化
  - `js/app.js` — 健康轮询(30s)、模型加载、Chat Playground（流式/非流式切换）
- 后端集成：
  - 添加 CORS 中间件（允许前端跨域调用 API）
  - 添加 StaticFiles 挂载 `/`（访问根路径直接展示 Dashboard）
  - `import os` 移至文件顶部
- 创建测试用户：`sk-relay-d0f56f1221c906cce79d4688a6e5e26a452df6b1621348ce`
- Playwright 验证：页面渲染正常、4 层矩阵动画、0 JS 错误、API 交互正常
- 全项目 Python 语法编译通过
