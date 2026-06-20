"""一次性脚本：创建测试用户并生成 API Key，打印 key 供测试使用"""
import asyncio
import hashlib
import hmac
import secrets

from app.core.config import settings
from app.db.base import async_session_factory
from app.db.models import ApiKey, User

async def main():
    raw_key = secrets.token_hex(24)
    key_hash = hmac.new(
        settings.secret_key.encode(),
        raw_key.encode(),
        hashlib.sha256
    ).hexdigest()
    async with async_session_factory() as s:
        user = User(username="admin", balance=100.0)
        s.add(user)
        await s.flush()
        s.add(ApiKey(user_id=user.id, key_hash=key_hash, label="default"))
        await s.commit()
    print(f"API Key: sk-relay-{raw_key}")

asyncio.run(main())
