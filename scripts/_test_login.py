"""测试 /v1/models 的完整链路"""
import asyncio
import httpx

async def main():
    async with httpx.AsyncClient() as c:
        # 1. 登录获取 JWT
        r = await c.post("http://127.0.0.1:8000/api/auth/login", json={"username": "admin", "password": "admin123"})
        if r.status_code != 200:
            print(f"LOGIN FAIL {r.status_code}: {r.text}")
            return
        token = r.json()["access_token"]
        print(f"Login OK, token: {token[:30]}...")

        # 2. 调用 /v1/models
        r2 = await c.get("http://127.0.0.1:8000/v1/models", headers={"Authorization": f"Bearer {token}"})
        print(f"/v1/models status: {r2.status_code}")
        if r2.status_code == 200:
            data = r2.json()
            models = data.get("data", [])
            print(f"模型数量: {len(models)}")
            for m in models[:5]:
                print(f"  {m['id']} | 价格={m.get('lowest_price')} | 上游数={m.get('upstream_count')} | 可用={m.get('available')}")
        else:
            print(f"Response: {r2.text[:300]}")

asyncio.run(main())
