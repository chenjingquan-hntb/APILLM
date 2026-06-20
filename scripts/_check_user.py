import asyncio
import bcrypt
from app.db.base import async_session_factory
from app.db.models import User
from sqlalchemy import select

async def main():
    async with async_session_factory() as s:
        r = await s.execute(select(User).where(User.username == 'admin'))
        u = r.scalar_one_or_none()
        if u and u.password_hash:
            h = u.password_hash.encode() if isinstance(u.password_hash, str) else u.password_hash
            print(f"hash bytes: {h}")
            print(f"hash len: {len(h)}")
            print(f"hash repr: {repr(h)}")
            ok = bcrypt.checkpw(b"admin123", h)
            print(f"verify: {ok}")
        else:
            print("no password hash")

asyncio.run(main())
