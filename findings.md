# Findings

## 2026-06-20：上游价格 API 兼容性调研

### 支流中转站价格接口摸底
- 大多数开源中转站（New API, One API）暴露 `/v1/models` 接口，部分返回 `pricing` 字段
- 没有标准化的价格字段，不同站点格式不同
- 需要可配置的爬取策略（字段映射）

### 易支付对接
- 易支付使用 MD5 签名，回调解耦
- 需要独立的回调端点，不依赖 WebSocket

## 2026-06-20：Python 3.14 兼容性

- SQLAlchemy async + greenlet 在 Python 3.14 正常（但必须用 selectinload 避免懒加载）
- httpx 流式响应在 async 上下文中 .text 不可用（ResponseNotRead）
- uvicorn 0.49+ 与 Python 3.14 兼容良好

## 架构决策记录

### ADR-1: ProxyError 分层
不使用 HTTPException 作为内部传播错误，因为 Starlette 会在流式响应中截断连接。创建 ProxyError(Exception) 由 chat.py 统一捕获转换。

### ADR-2: 直接加价制
用户价格 = 上游实际消耗价格 × (1 + markup_rate)，无需手动填写模型倍率。

### ADR-3: 双客户端策略
- `http_client` (120s timeout)：代理转发，支持长时间推理
- `_models_client` (10s timeout)：模型列表查询，快速失败

---

# 代码质量审查报告 — 2026-06-20

> 审查范围：Phase 1 + Phase 2 全部源码（23 个 .py 文件）
> 审查维度：安全 | 架构 | 错误处理 | 性能 | 测试
> 审查方式：5 个并行 Agent 独立审查 + 人工交叉验证

## 总体评分

| 维度 | 评分 | 评语 |
|------|------|------|
| 安全性 | **B-** | 无 RCE/注入漏洞，但存在前缀认证bug、Pydantic宽松校验、明文密钥 |
| 架构设计 | **B+** | 抽象层次合理（BaseProxyHandler→具体类），但全局状态和API层耦合需改进 |
| 错误处理 | **C+** | ProxyError分层是亮点，但大面积"裸异常"逃逸、异常链断裂、Redis崩溃级联 |
| 性能 | **B-** | async模式正确，但连接池/并发限制全靠默认值，高负载下会成为瓶颈 |
| 测试 | **D** | 无单元测试、无tests/目录、仅11个冒烟脚本。协议转换核心逻辑零覆盖 |
| **总评** | **C+** | 功能可用但**不可直接上生产**，需完成下方"P0 阻断项"后方可部署 |

---

## Critical — 必须在 Phase 3 前修复（共 8 项）

### C1. Redis 崩溃导致全链路级联失败
- **文件**: `app/services/redis.py:44-46`, `app/services/router.py:50`, `app/api/v1/chat.py:17`
- **现象**: `get_redis()` 在 `_client is None` 时抛出 `RuntimeError`。所有 Redis 操作 (`cache_get`, `cache_set`, `cache_mget`) 无 try/except。Redis 宕机后**每个 /v1/chat/completions 请求都崩溃**（因为 `rank_upstreams_by_model` 调用了 `cache_mget`）
- **修复**: 在每个 `cache_*` 函数内部加 try/except，返回安全默认值（`None` / `[]` / `0`），让业务降级到 priority-based 路由
- **多 agent 交叉确认**: 错误处理(C4) + 安全(H1可触发DoS) + 测试(C4) + 架构(Redis连接无health check)

### C2. 聊天端点无顶级异常处理器
- **文件**: `app/api/v1/chat.py:17-30`
- **现象**: `chat_completions` 整个 handler body 无 try/except。`rank_upstreams_by_model` → `cache_mget` → `get_redis()` → `RuntimeError` 直接变成裸 500，客户端收到零信息
- **修复**: 在 handler 外层加 `try...except AppError: raise; except Exception: raise UpstreamError(...)`

### C3. SSE 流中非 httpx 异常静默断连
- **文件**: `app/services/proxy/openai_proxy.py:24`、`app/services/proxy/anthropic_proxy.py:49`
- **现象**: `forward_stream` 的 try/except 只捕获 `(httpx.HTTPStatusError, httpx.RequestError)`。上游返回 200 但 JSON 畸形或 Pydantic 不兼容时，`model_validate_json()` 抛 `ValidationError` / `json.JSONDecodeError` 逃逸出生成器，Starlette 静默关闭 SSE——客户端看到截断流，无任何错误事件
- **修复**: 扩展 except 子句包含 `(json.JSONDecodeError, ValidationError)`，yield 一个 SSE 错误事件再 return

### C4. 健康检查数据未参与路由决策
- **文件**: `app/services/health_checker.py` + `app/api/v1/chat.py:22`
- **现象**: `check_all` 将 `healthy/degraded/unhealthy` 状态写入 Redis，但 `chat_completions` 从不读取——路由仅看 `Upstream.is_enabled`（由健康检查在达到 failure_threshold 后才更新 DB）。30s 窗口内刚故障的上游仍持续接收流量。Redis 健康数据实质上是**死代码**
- **修复**: 在 `rank_upstreams_by_model` 中读取 `HEALTH_KEY`，将 `unhealthy` 上游排除或降到最后

### C5. 无并发限制的 `asyncio.gather`
- **文件**: `app/api/v1/models.py:25`、`app/services/price_fetcher.py:57`、`app/services/health_checker.py:88`
- **现象**: 三处 `asyncio.gather(*tasks)` 均无 `Semaphore`。上游数增长到数十个时，瞬间打开数十个并发连接，可能导致文件描述符耗尽
- **修复**: 添加 `asyncio.Semaphore(10-20)` 限制并发

### C6. 数据库连接池默认值过小
- **文件**: `app/db/base.py:7`
- **现象**: `create_async_engine(...)` 未设置 `pool_size` 和 `max_overflow`，SQLAlchemy 默认 `pool_size=5, max_overflow=10`。每次认证请求占用 1 个连接（`last_used_at` write + commit），50 并发用户即瓶颈
- **修复**: 显式设置 `pool_size=20, max_overflow=20`

### C7. HTTP 连接池未显式配置
- **文件**: `app/services/proxy/base.py:9`、`app/api/v1/models.py:10`、`app/services/price_fetcher.py:10`、`app/services/health_checker.py:13`
- **现象**: 4 个 `httpx.AsyncClient` 均未设置 `limits`。默认 `max_connections=100`，LLM 流式响应持续 30-120s，100 个并发流即耗尽池
- **修复**: 为代理客户端设置 `limits=httpx.Limits(max_connections=200, max_keepalive_connections=50)`

### C8. 协议转换函数零单元测试
- **文件**: `app/schemas/anthropic.py:64-100`
- **现象**: `openai_to_anthropic()` 和 `anthropic_to_openai()` 是整个 Anthropic 中转链路的**核心正确性依赖**（纯函数、无 IO），但无任何测试。字段映射错误仅有真实用户流量能发现
- **修复**: 立即编写 `tests/test_anthropic_schema.py`，覆盖 system message 转换、多轮对话、stop_reason 全部映射、usage 计算、可选字段

---

## High — Phase 3 期间必须修复（共 10 项）

### H1. API Key 前缀导致认证失败 🔴
- **文件**: `app/services/auth.py:14-24` + `scripts/create_user.py` + `app/core/config.py:11`
- **现象**: `create_user.py` 生成 `sk-relay-{raw_key}` 并打印给用户。用户发送完整前缀字符串，但 `authenticate()` 对**整个含前缀字符串**计算 SHA-256，而数据库存储的是**无前缀**哈希 → **所有按文档使用打印 Key 的用户均认证失败**
- **修复**: 在 `authenticate()` 开头 strip `sk-relay-` 前缀，或 `create_user.py` 仅打印无前缀 raw_key
- **交叉确认**: 安全审查发现

### H2. Pydantic 模型未设 strict/forbid 模式
- **文件**: `app/schemas/openai.py:7`、`app/schemas/anthropic.py:14`
- **现象**: 所有 Pydantic 模型默认 `extra="ignore"`（而非 `"forbid"`），客户端传入非法字段不会收到 422，掩盖集成 bug。且缺少 `max_length` 约束各字段
- **修复**: 添加 `model_config = ConfigDict(extra="forbid")`，关键字段加 `max_length`

### H3. 异常链全部断裂（0 处 `raise ... from`）
- **文件**: 整个项目 32 个 .py 文件，0 处使用 `raise ... from`
- **现象**: `_raise_for_http_error` 中 `raise ProxyError(msg)` 丢弃原始异常和 traceback。调试时只能看到笼统的 `ProxyError`，不知道是 `ConnectError`、`ReadTimeout` 还是 `HTTPStatusError`
- **修复**: 全局 `raise ProxyError(msg) from e`

### H4. HTTP 客户端使用平面超时
- **文件**: 全部 4 个 `httpx.AsyncClient`：`timeout=120.0`
- **现象**: 单一浮点数超时同等应用于 connect/read/write/pool。连接死上游等 120s；慢 LLM 流式首字节可能被误杀
- **修复**: 使用 `httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=10.0)`

### H5. 非流式 forward 未捕获 JSON/Pydantic 错误
- **文件**: `app/services/proxy/openai_proxy.py:16-18`、`app/services/proxy/anthropic_proxy.py:29`
- **现象**: `resp.json()` 和 `ChatCompletionResponse.model_validate()` 异常逃逸 → 裸 500。与 C3 同类但影响非流式路径
- **修复**: except 子句增加 `(json.JSONDecodeError, ValidationError)`

### H6. 流式 failover 生成器静默死亡
- **文件**: `app/api/v1/chat.py:55-73`
- **现象**: `_stream()` 生成器内部 try/except 只捕获 `ProxyError`。非 ProxyError 异常（JSON 崩溃、Redis 故障）逃逸 → Starlette 静默切断 SSE，客户端无错误事件
- **修复**: 最外层加 `except Exception`，yield SSE 错误事件 + 日志 `exc_info=True`

### H7. Redis 无自动重连机制
- **文件**: `app/services/redis.py:19-22`
- **现象**: `init_redis()` 成功后 `_client` 永不过期。Redis 重启后连接池中的旧连接全部失效（无 `pool_pre_ping` 等价物），所有后续操作失败直到 app 重启
- **修复**: 实现重连模式——在 `ConnectionError` 时关闭旧池、创建新池、重试一次

### H8. 每个认证请求都写入数据库
- **文件**: `app/services/auth.py:22-27`
- **现象**: 每次 `authenticate()` 成功后更新 `last_used_at` + `session.commit()`。这在高并发下成为 DB 瓶颈——每个请求额外一次写事务
- **修复**: 将 `last_used_at` 更新异步化（如写入 Redis 定期批量刷 DB），或接受此为可承受开销（当前 Phase 2 阶段可接受）

### H9. 上游 API Key 明文存储
- **文件**: `app/db/models.py:40` — `Upstream.api_key: Mapped[str] = mapped_column(String(256))`
- **现象**: 上游提供商的 API 密钥以明文存入 PostgreSQL。数据库被攻破 → 所有上游密钥泄露
- **修复**: 使用应用层加密（如 `cryptography.fernet` + `settings.secret_key`），或至少在 Vault/KMS 就绪前记录为债务

### H10. 无 SSRF 防护
- **文件**: `app/services/proxy/base.py:13-14`、所有调用 `build_url()` 的位置
- **现象**: `build_url(base_url, path)` 简单字符串拼接，无 URL 解析/IP 校验。若攻击者能修改数据库中的 `base_url`（需已获 DB 访问），可构造 SSRF payload（如 `http://169.254.169.254/latest/meta-data/`）
- **缓解**: 当前 `Upstream.base_url` 仅管理员可写入（未来 Phase 3 管理后台）。但 `httpx.AsyncClient` 应显式设置 `follow_redirects=False`

---

## Medium — Phase 3 期间建议修复（共 10 项）

### M1. 健康检查启动后延迟一个周期
- **文件**: `app/services/health_checker.py:106-118` — `run_health_loop` **先 `sleep` 再 `check_all`**
- **修复**: 将 sleep 移到 check_all 之后

### M2. 健康检查健康状态无 TTL
- **文件**: `app/services/health_checker.py:59-81` — `cache_set(key, state)` 未传 `ttl`
- **修复**: 传 `ttl=settings.health_check_interval * 3`

### M3. health endpoint 静态无依赖检查
- **文件**: `app/api/health.py:6-8` — 返回硬编码 `{"status": "ok"}`
- **修复**: 添加 Redis PING + DB SELECT 1，失败返回 503

### M4. 空上游列表时错误消息为空
- **文件**: `app/api/v1/chat.py:37` — `"; ".join(errors)` 在 `errors=[]` 时产生空字符串
- **修复**: 在 failover 函数开头加 `if not upstreams: raise NoAvailableUpstreamError()`

### M5. SHA-256 无盐、无恒定时间比较
- **文件**: `app/services/auth.py:11-12` — `hashlib.sha256(raw_key.encode()).hexdigest()` 无 salt
- **实际风险**: 低（key 是 `secrets.token_hex(24)` 48 字符 hex，强随机），但最佳实践要求至少加 pepper
- **修复**: HMAC-SHA256(key, pepper=settings.secret_key) 或 bcrypt

### M6. 裸 `except Exception` 吞没关键信息
- **文件**: `app/api/v1/models.py:27`、`app/services/price_fetcher.py:118`、`app/services/health_checker.py:116`
- **修复**: 缩小到 `except (httpx.HTTPError, asyncio.TimeoutError)`

### M7. failover 在 API 层而非 service 层
- **文件**: `app/api/v1/chat.py:30-70` — `_non_stream_with_failover` 和 `_stream_with_failover` 直接写在路由文件中
- **修复**: 提取到 `app/services/chat_service.py`

### M8. `auth_header()` 定义但 openai_proxy 未使用
- **文件**: `app/services/proxy/base.py:17-18` vs `app/services/proxy/openai_proxy.py:14`
- **修复**: openai_proxy 统一使用 `auth_header(upstream.api_key)`

### M9. 价格获取器双重超时
- **文件**: `app/services/price_fetcher.py:57-61` — `_price_client(timeout=10s)` + 外层 `asyncio.wait_for(timeout=8s)` 双重超时
- **修复**: 统一使用 httpx 超时，去掉外层 `wait_for`

### M10. 日志可能泄露凭据
- **文件**: `app/services/redis.py:21` — `logger.info("redis_connected", url=settings.redis_url)` 输出完整 Redis URL（含密码）
- **修复**: 脱敏处理 URL（隐藏密码段）

---

## Low — 后续迭代处理（共 6 项）

| # | 问题 | 文件 |
|---|------|------|
| L1 | `smoke_test_phase2.py:217` finally 块 `cleanup(upstreams)` — 若 `setup_db()` 失败则 `upstreams` 未定义 | `scripts/smoke_test_phase2.py` |
| L2 | `run_price_fetch_loop` / `run_health_loop` `except Exception` 虽然已 `exc_info=True` 但可能隐藏编程错误 | `price_fetcher.py:118`, `health_checker.py:116` |
| L3 | 缺少 `pool_recycle=3600` — 长生命后台循环可能用过期 DB 连接 | `app/db/base.py:7` |
| L4 | 流式 failover 切换上游时 chunk ID 变化 — OpenAI 兼容客户端可能拒绝 | `app/api/v1/chat.py:48-70` |
| L5 | Anthropic 未知 stop_reason 静默映射到 "stop"，应加 DEBUG 日志 | `app/services/proxy/anthropic_proxy.py:62` |
| L6 | `cache_get`/`cache_mget` 返回类型标注 `-> dict` 不准确（`json.loads` 可返回 list） | `app/services/redis.py:39,70` |

---

## 修复优先级路线图

```
Phase 2.5 (当前): 安全加固 + 错误处理    [预计 3-5 天]
├── 🔴 P0-阻断: C1 C2 C3 C4 C5 C6 C7 C8 (8项)
├── 🟠 P1-紧急: H1 H2 H3 H4 H5 H6 H7 H8 H9 H10 (10项)
└── 🟡 P2-重要: M1~M10 (10项)
                    ↓
Phase 3 (商业化): 余额扣费 + 易支付    [预计 5-7 天]
├── 依赖 Phase 2.5 全部 P0/P1 完成
└── 新增: 管理后台 CRUD、调用日志、账单明细
                    ↓
Phase 3.5: 测试体系建设                 [预计 3-5 天]
├── 创建 tests/ 目录 + conftest.py
├── P0: test_anthropic_schema.py, test_router.py, test_auth.py
├── P1: test_health_checker.py, test_chat_api.py, test_price_fetcher.py
└── P2: test_redis.py, test_e2e.py
```

---

## 架构决策记录（续）

### ADR-4: 全局状态重构方向
当前模块级 `http_client` / `_redis_client` / `_health_client` 等全局单例阻碍测试隔离。Phase 3 前应引入依赖注入：
- Redis 客户端 → `RedisClient` 类，在 lifespan 中实例化，通过 `Depends` 传递
- HTTP 客户端 → 每个 ProxyHandler 构造时注入（而非模块级共享）
- Settings → 通过 `get_settings` dependency 注入（而非全局 import `settings`）

### ADR-5: 路由健康感知
`rank_upstreams_by_model` 应在价格排序后检查 Redis 健康状态，将 `unhealthy` 上游移至末尾或排除。避免当前 "健康数据写入 Redis 但无人读取" 的架构浪费。
