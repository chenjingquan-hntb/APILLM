import asyncio, httpx

async def main():
    async with httpx.AsyncClient() as c:
        r = await c.post("http://127.0.0.1:8000/api/auth/login", json={"username": "admin", "password": "admin123"})
        print(f"status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"access_token: {data.get('access_token','')[:30]}...")
        else:
            print(r.text)

asyncio.run(main())
