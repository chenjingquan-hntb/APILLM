"""全面健康检查脚本 — 覆盖所有组件和核心功能链路。

运行方式:
  python scripts/healthcheck.py                   # 检查所有组件
  python scripts/healthcheck.py --skip-redis      # 跳过 Redis 检查
  python scripts/healthcheck.py --verbose         # 详细输出
  python scripts/healthcheck.py --endpoint http://localhost:8000  # 自定义端点

退出码: 0=全部通过, 1=部分失败, 2=严重失败
"""
import argparse
import asyncio
import json
import os
import sys
import time
from enum import Enum, auto

import httpx

BASE = os.environ.get("HEALTHCHECK_BASE", "http://127.0.0.1:8000")
TIMEOUT = 15.0


class Status(Enum):
    PASS = auto()
    WARN = auto()
    FAIL = auto()


results: list[tuple[str, Status, str]] = []
start_time = 0.0


def log(name: str, status: Status, detail: str = ""):
    elapsed = time.monotonic() - start_time
    icon = {Status.PASS: "✓", Status.WARN: "⚠", Status.FAIL: "✗"}[status]
    label = {Status.PASS: "PASS", Status.WARN: "WARN", Status.FAIL: "FAIL"}[status]
    print(f"  [{label}] {icon} {name} ({elapsed:.1f}s)" + (f" — {detail}" if detail else ""))
    results.append((name, status, detail))


def passed() -> int:
    """Return 0 if all pass, 1 if any warn, 2 if any fail."""
    has_fail = any(s == Status.FAIL for _, s, _ in results)
    has_warn = any(s == Status.WARN for _, s, _ in results)
    if has_fail:
        return 2
    if has_warn:
        return 1
    return 0


# ============================================================
# Component checks
# ============================================================


async def check_http_endpoint(client: httpx.AsyncClient, method: str, path: str, **kwargs) -> httpx.Response:
    url = f"{BASE}{path}"
    try:
        resp = await client.request(method, url, timeout=TIMEOUT, **kwargs)
        return resp
    except httpx.ConnectError:
        raise ConnectionError(f"Cannot connect to {BASE} — is the server running?")


async def check_health(client: httpx.AsyncClient):
    """GET /health — server must be alive."""
    try:
        resp = await check_http_endpoint(client, "GET", "/health")
        data = resp.json()
        if resp.status_code == 200 and "status" in data:
            log("GET /health", Status.PASS, f"status={data['status']}")
        else:
            log("GET /health", Status.FAIL, f"unexpected response: {resp.status_code}")
    except Exception as e:
        log("GET /health", Status.FAIL, str(e))


async def check_auth_endpoints(client: httpx.AsyncClient):
    """POST /api/auth/login — login endpoint works with proper error handling."""
    try:
        # Empty body — should return 422
        resp = await check_http_endpoint(client, "POST", "/api/auth/login", json={})
        if resp.status_code == 422:
            log("POST /api/auth/login (validation)", Status.PASS)
        else:
            log("POST /api/auth/login (validation)", Status.FAIL, f"expected 422, got {resp.status_code}")

        # Wrong credentials — should return 401
        resp = await check_http_endpoint(client, "POST", "/api/auth/login", json={
            "username": "nonexistent",
            "password": "wrong",
        })
        if resp.status_code == 401:
            log("POST /api/auth/login (wrong creds)", Status.PASS)
        else:
            log("POST /api/auth/login (wrong creds)", Status.FAIL, f"expected 401, got {resp.status_code}")
    except Exception as e:
        log("POST /api/auth/login", Status.FAIL, str(e))


async def check_auth_rejection(client: httpx.AsyncClient):
    """Unauthenticated requests to /v1 should be rejected."""
    try:
        resp = await check_http_endpoint(client, "GET", "/v1/models")
        if resp.status_code in (401, 403):
            log("GET /v1/models (auth rejection)", Status.PASS)
        else:
            log("GET /v1/models (auth rejection)", Status.FAIL, f"expected 401/403, got {resp.status_code}")
    except Exception as e:
        log("GET /v1/models (auth rejection)", Status.FAIL, str(e))


async def check_admin_auth_rejection(client: httpx.AsyncClient):
    """Admin endpoints require authentication."""
    try:
        resp = await check_http_endpoint(client, "GET", "/api/admin/upstreams")
        if resp.status_code in (401, 403):
            log("GET /api/admin/upstreams (auth rejection)", Status.PASS)
        else:
            log("GET /api/admin/upstreams (auth rejection)", Status.FAIL, f"expected 401/403, got {resp.status_code}")
    except Exception as e:
        log("GET /api/admin/upstreams (auth rejection)", Status.FAIL, str(e))


async def check_redis_available(client: httpx.AsyncClient):
    """Check if Redis is available via health endpoint."""
    try:
        resp = await check_http_endpoint(client, "GET", "/health")
        data = resp.json()
        redis_status = data.get("redis", data.get("services", {}).get("redis", "unknown"))
        if redis_status in ("ok", "healthy", "connected"):
            log("Redis 连接", Status.PASS, str(redis_status))
        elif redis_status in ("disconnected", "unavailable"):
            log("Redis 连接", Status.WARN, f"Redis 不可用: {redis_status}")
        else:
            log("Redis 连接", Status.WARN, f"状态未知: {redis_status}")
    except Exception as e:
        log("Redis 连接", Status.WARN, str(e))


async def check_database_available(client: httpx.AsyncClient):
    """Check if database is available via health endpoint."""
    try:
        resp = await check_http_endpoint(client, "GET", "/health")
        data = resp.json()
        db_status = data.get("database", data.get("services", {}).get("database", "unknown"))
        if db_status in ("ok", "healthy", "connected"):
            log("数据库连接", Status.PASS, str(db_status))
        elif db_status in ("disconnected", "unavailable"):
            log("数据库连接", Status.FAIL, f"数据库不可用: {db_status}")
        else:
            log("数据库连接", Status.WARN, f"状态未知: {db_status}")
    except Exception as e:
        log("数据库连接", Status.FAIL, str(e))


async def check_openapi_docs(client: httpx.AsyncClient):
    """OpenAPI docs available in debug mode."""
    try:
        resp = await check_http_endpoint(client, "GET", "/docs")
        if resp.status_code == 200:
            log("OpenAPI /docs", Status.PASS)
        elif resp.status_code == 404:
            log("OpenAPI /docs", Status.WARN, "docs 被禁用 (debug=False)")
        else:
            log("OpenAPI /docs", Status.FAIL, f"unexpected: {resp.status_code}")
    except Exception as e:
        log("OpenAPI /docs", Status.FAIL, str(e))


async def check_cors_headers(client: httpx.AsyncClient):
    """CORS headers should be present on API responses."""
    try:
        resp = await check_http_endpoint(client, "GET", "/health")
        cors = resp.headers.get("access-control-allow-origin", "")
        if cors == "*":
            log("CORS 头", Status.PASS)
        else:
            log("CORS 头", Status.WARN, f"unexpected origin: '{cors}'")
    except Exception as e:
        log("CORS 头", Status.FAIL, str(e))


async def check_frontend_served(client: httpx.AsyncClient):
    """Frontend static files should be served at root."""
    try:
        resp = await check_http_endpoint(client, "GET", "/")
        if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""):
            log("前端静态文件", Status.PASS)
        elif resp.status_code == 404:
            log("前端静态文件", Status.WARN, "静态目录未配置或不存在")
        else:
            log("前端静态文件", Status.WARN, f"响应 {resp.status_code}")
    except Exception as e:
        log("前端静态文件", Status.FAIL, str(e))


async def check_admin_api(client: httpx.AsyncClient, admin_token: str):
    """Test admin API endpoints if token available."""
    if not admin_token:
        log("Admin API 端点", Status.WARN, "跳过 — 未提供管理令牌")
        return

    headers = {"Authorization": f"Bearer {admin_token}"}
    endpoints = [
        ("GET", "/api/admin/upstreams", "获取上游列表"),
        ("GET", "/api/admin/models", "获取模型配置"),
        ("GET", "/api/admin/users", "获取用户列表"),
        ("GET", "/api/admin/stats/overview", "获取概览统计"),
        ("GET", "/api/admin/logs?page=1&size=5", "获取日志列表"),
    ]
    for method, path, label in endpoints:
        try:
            resp = await check_http_endpoint(client, method, path, headers=headers)
            if resp.status_code == 200:
                log(f"Admin API: {label}", Status.PASS)
            else:
                log(f"Admin API: {label}", Status.FAIL, f"{resp.status_code}: {resp.text[:100]}")
        except Exception as e:
            log(f"Admin API: {label}", Status.FAIL, str(e))


# ============================================================
# Main
# ============================================================


async def main():
    global start_time
    parser = argparse.ArgumentParser(description="LLM Relay 全面健康检查")
    parser.add_argument("--endpoint", default=BASE, help="API 端点地址")
    parser.add_argument("--admin-token", default="", help="Admin JWT 令牌 (用于测试管理 API)")
    parser.add_argument("--skip-redis", action="store_true", help="跳过 Redis 检查")
    parser.add_argument("--skip-frontend", action="store_true", help="跳过前端检查")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    args = parser.parse_args()

    os.environ["HEALTHCHECK_BASE"] = args.endpoint
    print("LLM Relay 全面健康检查")
    print(f"{'=' * 50}")
    print(f"端点: {args.endpoint}")
    print(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    start_time = time.monotonic()

    async with httpx.AsyncClient() as client:
        # ========== Layer 1: Core Infrastructure ==========
        print("[1/5] 核心基础设施")
        print("-" * 30)
        await check_health(client)
        await check_database_available(client)
        if not args.skip_redis:
            await check_redis_available(client)
        print()

        # ========== Layer 2: API Layer ==========
        print("[2/5] API 层")
        print("-" * 30)
        await check_auth_endpoints(client)
        await check_auth_rejection(client)
        await check_admin_auth_rejection(client)
        await check_openapi_docs(client)
        await check_cors_headers(client)
        print()

        # ========== Layer 3: Admin API ==========
        print("[3/5] 管理 API")
        print("-" * 30)
        await check_admin_api(client, args.admin_token)
        print()

        # ========== Layer 4: Frontend ==========
        print("[4/5] 前端")
        print("-" * 30)
        if not args.skip_frontend:
            await check_frontend_served(client)
        else:
            log("前端", Status.WARN, "跳过")
        print()

        # ========== Summary ==========
        print("[5/5] 汇总")
        print("-" * 30)
        total = len(results)
        passed_count = sum(1 for _, s, _ in results if s == Status.PASS)
        warned_count = sum(1 for _, s, _ in results if s == Status.WARN)
        failed_count = sum(1 for _, s, _ in results if s == Status.FAIL)
        elapsed = time.monotonic() - start_time

        print(f"  总计: {total} 项检查")
        print(f"  通过: {passed_count}")
        print(f"  警告: {warned_count}")
        print(f"  失败: {failed_count}")
        print(f"  耗时: {elapsed:.1f}s")
        print()

        if args.verbose and warned_count + failed_count > 0:
            print("⚠ 警告/失败详情:")
            for name, status, detail in results:
                if status != Status.PASS:
                    print(f"  [{status.name}] {name}: {detail}")
            print()

        if failed_count == 0:
            print("✓ 全部通过 — 系统健康")
        elif warned_count > 0 and failed_count == 0:
            print("⚠ 已通过，但存在警告")
        else:
            print(f"✗ {failed_count} 项检查失败")

        return passed()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
