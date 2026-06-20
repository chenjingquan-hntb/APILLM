# Task Plan — LLM Relay (API 中转站中站)

## Goal
构建一套"API中转站的中转站"：对接多个上游模型中转站，自动监控定价、智能路由低价站点、简化为直接加价制，兼容易支付。

## Phase 1: 核心基础架构 — ✅ 完成

- [x] FastAPI 异步服务框架 + 结构化日志
- [x] 数据库层：User / ApiKey / Upstream ORM + Alembic 迁移
- [x] SHA-256 API Key 认证（selectinload eager load）
- [x] OpenAI 协议代理转发（非流式 + SSE 流式）
- [x] Anthropic 协议代理转发（请求/响应双向转换，含流式 SSE 转换）
- [x] Priority 优先级上游路由
- [x] GET /v1/models 并发聚合
- [x] 统一异常体系（AppError + ProxyError 分层）
- [x] 冒烟测试 6/6 通过

## Phase 2: 价格监控与智能路由 — ✅ 完成

- [x] Redis 基础设施：连接池管理，封装 cache_get/set/delete/mget
- [x] 上游价格抓取器：定时调用各上游 /v1/models 获取模型定价
- [x] 价格缓存：Redis 缓存上游报价，支持 TTL 过期
- [x] 智能路由器：按模型-价格排序选择最便宜可用上游
- [x] 上游健康检测：定期 ping + 自动禁用/启用
- [x] 故障切换：请求失败自动重试下一个上游
- [x] 冒烟测试 5/5 通过

## Phase 2.5: 前端展示 Dashboard — ✅ 完成

- [x] Web/ 纯静态前端（index.html + css/style.css + js/api.js + js/app.js）
- [x] MiMo 风格 Hero 文字矩阵动画（4 层 "A P I L L M / R E L A Y / P R O X Y" 视差滚动）
- [x] 系统健康面板（Redis/DB 状态灯 + 30s 自动轮询）
- [x] 模型列表展示（调用 GET /v1/models 动态加载）
- [x] API Playground（Chat Completions 在线测试，支持流式 SSE / 非流式切换）
- [x] Quick Start 代码示例（Python SDK + curl，一键复制）
- [x] 后端 CORS 中间件 + StaticFiles 挂载 `/`
- [x] Playwright 自动化验证（0 JS 错误，全部元素可见）
- [x] design-system/ 设计文档持久化

## Phase 3: 商业化 — ⏳ 待实现

- [ ] 用户余额扣费（上游实际消耗 × (1 + markup_rate)）
- [ ] 易支付原生集成
- [ ] 管理后台 API（CRUD 上游/用户）
- [ ] 调用日志与账单明细

## Errors Encountered
| Error | Phase | Resolution |
|-------|-------|------------|
| MissingGreenlet in auth | 1 | selectinload() 替代 join() |
| HTTPException 截断 SSE 流 | 1 | 新增 ProxyError(Exception) 分层 |
| ResponseNotRead in _raise_for_http_error | 1 | 改用 status_code 而非 .text |
| alembic script.py.mako missing | 1 | 手动创建模板 |
| health_checker needs all upstreams for auto-recovery | 2 | check_all uses list() without filters, not get_enabled() |
| rank_upstreams returns list for failover iteration | 2 | rank_upstreams_by_model() gives sorted list, select_upstream_by_model() takes [0]
