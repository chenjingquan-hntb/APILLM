"""Phase 2 smoke test: price monitoring, smart routing, health check, failover"""
import asyncio
import json
import sys
import os
import secrets
import hashlib
from http.server import HTTPServer, BaseHTTPRequestHandler

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import async_session_factory
from app.db.models import User, ApiKey, Upstream, UpstreamProtocol
from app.services.redis import init_redis, close_redis, cache_set, cache_get, cache_delete, PRICE_KEY_FMT, HEALTH_KEY
from app.services.router import rank_upstreams_by_model, select_upstream, select_upstream_by_model
from app.services.health_checker import _update_health
from app.services.price_fetcher import _fetch_one, store_pricing
from app.core.exceptions import NoAvailableUpstreamError

MOCK_PORT = 18081
MOCK_HOST = "127.0.0.1"


class MockUpstreamHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/v1/models":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            resp = {
                "object": "list",
                "data": [
                    {"id": "gpt-4o", "object": "model", "created": 1718841600, "pricing": {"prompt": 0.005, "completion": 0.015}},
                    {"id": "claude-sonnet-4-6", "object": "model", "created": 1718841600, "pricing": {"prompt": 0.003, "completion": 0.012}},
                ],
            }
            self.wfile.write(json.dumps(resp).encode())
        elif self.path == "/v1/chat/completions":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            resp = {
                "id": "chatcmpl-mock", "object": "chat.completion", "created": 1718841600,
                "model": "gpt-4o",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "hello from mock"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
            }
            self.wfile.write(json.dumps(resp).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


async def setup_db() -> tuple[str, list[Upstream]]:
    raw_key = secrets.token_hex(24)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    from sqlalchemy import text

    async with async_session_factory() as s:
        await s.execute(text("DELETE FROM api_keys WHERE label = 'phase2-test'"))
        await s.execute(text("DELETE FROM users WHERE username = 'phase2-tester'"))
        await s.execute(text("DELETE FROM upstreams WHERE name LIKE 'phase2-%'"))
        await s.flush()

        user = User(username="phase2-tester", balance=100.0)
        s.add(user)
        await s.flush()
        s.add(ApiKey(user_id=user.id, key_hash=key_hash, label="phase2-test"))

        s.add(Upstream(
            name="phase2-expensive", base_url="http://127.0.0.1:19999", api_key="sk-dead",
            protocol=UpstreamProtocol.openai, priority=50, is_enabled=True,
            pricing_config={"model_id_field": "id", "prompt_price_field": "pricing.prompt", "completion_price_field": "pricing.completion"},
        ))

        s.add(Upstream(
            name="phase2-cheap", base_url=f"http://{MOCK_HOST}:{MOCK_PORT}", api_key="sk-mock",
            protocol=UpstreamProtocol.openai, priority=10, is_enabled=True,
            pricing_config={"model_id_field": "id", "prompt_price_field": "pricing.prompt", "completion_price_field": "pricing.completion"},
        ))

        await s.commit()

        from sqlalchemy import select
        result = await s.execute(select(Upstream).where(Upstream.name.like("phase2-%")))
        upstreams = list(result.scalars().all())

    return raw_key, upstreams


async def test_price_fetcher(upstreams: list[Upstream]):
    mock_upstream = next(u for u in upstreams if u.name == "phase2-cheap")
    results = await _fetch_one(mock_upstream)
    assert len(results) == 2, f"Expected 2 models, got {len(results)}"
    assert results[0]["prompt"] == 0.005
    assert results[0]["completion"] == 0.015

    await store_pricing({mock_upstream.id: results})

    cached = await cache_get(PRICE_KEY_FMT.format(mock_upstream.id, "gpt-4o"))
    assert cached is not None, "Price not cached in Redis"
    assert cached["prompt"] == 0.005

    await cache_delete(PRICE_KEY_FMT.format(mock_upstream.id, "gpt-4o"), PRICE_KEY_FMT.format(mock_upstream.id, "claude-sonnet-4-6"))
    print("[PASS] price fetcher: extract and cache pricing")


async def test_smart_router(upstreams: list[Upstream]):
    mock = next(u for u in upstreams if u.name == "phase2-cheap")
    dead = next(u for u in upstreams if u.name == "phase2-expensive")

    await cache_set(PRICE_KEY_FMT.format(mock.id, "gpt-4o"), {"prompt": 0.001, "completion": 0.003, "currency": "CNY", "updated_at": 0})
    await cache_set(PRICE_KEY_FMT.format(dead.id, "gpt-4o"), {"prompt": 0.050, "completion": 0.150, "currency": "CNY", "updated_at": 0})

    best = await select_upstream_by_model(upstreams, "gpt-4o")
    assert best.id == mock.id, f"Expected cheapest {mock.name}, got {best.name}"

    ranked = await rank_upstreams_by_model(upstreams, "gpt-4o")
    assert ranked[0].id == mock.id
    assert ranked[1].id == dead.id

    await cache_delete(PRICE_KEY_FMT.format(mock.id, "gpt-4o"), PRICE_KEY_FMT.format(dead.id, "gpt-4o"))
    print("[PASS] smart router: select cheapest upstream")


async def test_router_fallback(upstreams: list[Upstream]):
    best = await select_upstream_by_model(upstreams, "unknown-model")
    assert best.priority == 50, f"Expected priority 50 as fallback, got {best.priority}"
    print("[PASS] router fallback: priority-based when no price data")


async def test_health_checker(upstreams: list[Upstream]):
    mock = next(u for u in upstreams if u.name == "phase2-cheap")

    for _ in range(3):
        await _update_health(mock, False)

    state = await cache_get(HEALTH_KEY.format(mock.id))
    assert state["status"] == "unhealthy"
    assert state["consecutive_failures"] >= 3

    for _ in range(2):
        await _update_health(mock, True)

    state = await cache_get(HEALTH_KEY.format(mock.id))
    assert state["status"] == "healthy"

    await cache_delete(HEALTH_KEY.format(mock.id))
    print("[PASS] health checker: state machine transitions correct")


async def test_no_upstream_error():
    try:
        select_upstream([])
        assert False, "Should have raised"
    except NoAvailableUpstreamError:
        pass
    print("[PASS] failover: correct exception on empty upstreams")


async def cleanup(upstreams: list[Upstream]):
    for u in upstreams:
        await cache_delete(HEALTH_KEY.format(u.id))
    from sqlalchemy import text
    async with async_session_factory() as s:
        await s.execute(text("DELETE FROM api_keys WHERE label = 'phase2-test'"))
        await s.execute(text("DELETE FROM users WHERE username = 'phase2-tester'"))
        await s.execute(text("DELETE FROM upstreams WHERE name LIKE 'phase2-%'"))
        await s.commit()


async def main():
    print("=== Phase 2 Smoke Test Suite ===\n")

    mock_server = HTTPServer((MOCK_HOST, MOCK_PORT), MockUpstreamHandler)
    server_thread = None

    try:
        print("[setup] initializing Redis...")
        await init_redis()

        print("\n[setup] creating test data...")
        api_key, upstreams = await setup_db()
        print(f"      Test API Key: sk-relay-{api_key}")

        import threading
        server_thread = threading.Thread(target=mock_server.serve_forever, daemon=True)
        server_thread.start()
        print(f"      Mock upstream on http://{MOCK_HOST}:{MOCK_PORT}")

        print("\n[1/5] price fetcher...")
        await test_price_fetcher(upstreams)

        print("\n[2/5] smart router...")
        await test_smart_router(upstreams)

        print("\n[3/5] router fallback...")
        await test_router_fallback(upstreams)

        print("\n[4/5] health checker...")
        await test_health_checker(upstreams)

        print("\n[5/5] failover...")
        await test_no_upstream_error()

    finally:
        if server_thread:
            mock_server.shutdown()
        try:
            await cleanup(upstreams)
        except Exception:
            pass
        await close_redis()

    print("\n=== ALL 5 PHASE 2 TESTS PASSED ===")


if __name__ == "__main__":
    asyncio.run(main())
