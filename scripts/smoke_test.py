"""冒烟测试：覆盖数据库、认证、代理、转发全链路"""
import asyncio
import hashlib
import hmac
import json
import os
import secrets
import sys

import httpx

BASE = "http://127.0.0.1:8000"

# 添加上游模块到 path (必须在 app 模块导入之前)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db.base import async_session_factory  # noqa: E402
from app.db.models import User, ApiKey, Upstream, UpstreamProtocol  # noqa: E402


async def setup() -> str:
    """幂等：创建测试用户并返回 API Key"""
    raw_key = secrets.token_hex(24)
    key_hash = hmac.new(
        settings.secret_key.encode(),
        raw_key.encode(),
        hashlib.sha256
    ).hexdigest()
    from sqlalchemy import text
    async with async_session_factory() as s:
        await s.execute(text("DELETE FROM api_keys WHERE label = 'test'"))
        await s.execute(text("DELETE FROM users WHERE username = 'tester'"))
        await s.flush()
        user = User(username="tester", balance=100.0)
        s.add(user)
        await s.flush()
        s.add(ApiKey(user_id=user.id, key_hash=key_hash, label="test"))
        await s.commit()
    return raw_key


async def seed_upstream():
    async with async_session_factory() as s:
        from sqlalchemy import text
        await s.execute(text("DELETE FROM upstreams WHERE name = 'test-mock'"))
        await s.commit()

    async with async_session_factory() as s:
        s.add(Upstream(
            name="test-mock",
            base_url="http://127.0.0.1:18080",
            api_key="sk-test",
            protocol=UpstreamProtocol.openai,
            priority=10,
        ))
        await s.commit()


async def test_health(client: httpx.AsyncClient):
    resp = await client.get(f"{BASE}/health")
    assert resp.status_code == 200, f"health fail: {resp.status_code}"
    data = resp.json()
    assert data["status"] in ("ok", "degraded"), f"unexpected health status: {data}"
    print(f"[PASS] GET /health — status={data['status']}")


async def test_auth_rejected(client: httpx.AsyncClient):
    resp = await client.get(f"{BASE}/v1/models")
    assert resp.status_code == 401 or resp.status_code == 403, f"expected 401/403 got {resp.status_code}"
    print(f"[PASS] 匿名请求被拒绝: {resp.status_code}")


async def test_models(client: httpx.AsyncClient, api_key: str):
    resp = await client.get(
        f"{BASE}/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert resp.status_code == 200, f"models fail: {resp.status_code} {resp.text}"
    data = resp.json()
    assert data["object"] == "list"
    print(f"[PASS] GET /v1/models — {len(data['data'])} models")


async def test_chat_upstream_error(client: httpx.AsyncClient, api_key: str):
    """上游不可达时返回 502"""
    resp = await client.post(
        f"{BASE}/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": False,
        },
    )
    assert resp.status_code == 502, f"expected 502 got {resp.status_code}"
    body = resp.json()
    assert "upstream_error" in str(body)
    print("[PASS] POST /v1/chat/completions — 上游不可达返回 502")


async def test_chat_stream_upstream_error(client: httpx.AsyncClient, api_key: str):
    """上游流式不可达 — 响应仍应为 SSE 含错误"""
    async with client.stream(
        "POST",
        f"{BASE}/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": True,
        },
    ) as resp:
        assert resp.status_code == 200, f"SSE 应返回 200，实际 {resp.status_code}"
        body = b""
        async for line in resp.aiter_lines():
            if line.startswith("data: "):
                body += line.encode()
        text = body.decode()
        assert "error" in text.lower(), f"SSE 应含 error: {text[:200]}"
        print("[PASS] POST /v1/chat/completions (stream) — 上游错误正确编码为 SSE")


async def main():
    print("=== Smoke Test Suite ===\n")

    print("[1/6] 创建测试数据...")
    api_key = await setup()
    await seed_upstream()
    print(f"      Test API Key: sk-relay-{api_key}")

    async with httpx.AsyncClient(timeout=30) as client:
        print("\n[2/6] 健康检查...")
        await test_health(client)

        print("\n[3/6] 认证拦截...")
        await test_auth_rejected(client)

        print("\n[4/6] 模型列表...")
        await test_models(client, api_key)

        print("\n[5/6] 上游不可达错误...")
        await test_chat_upstream_error(client, api_key)

        print("\n[6/6] 流式上游错误...")
        await test_chat_stream_upstream_error(client, api_key)

    print("\n=== ALL 6 TESTS PASSED ===")


if __name__ == "__main__":
    asyncio.run(main())
