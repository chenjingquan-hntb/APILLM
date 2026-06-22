"""CI helper — create test admin user and output JWT token for healthcheck."""
import asyncio
import sys
from app.db.base import async_session_factory
from app.db.models import User
from app.services.auth import hash_password
from app.services.jwt import create_access_token


async def main():
    async with async_session_factory() as s:
        from sqlalchemy import text
        await s.execute(text("DELETE FROM users WHERE username = 'health-admin'"))
        await s.flush()
        u = User(username="health-admin", password_hash=hash_password("health-pass"), role="admin")
        s.add(u)
        await s.commit()
        await s.refresh(u)
        uid = u.id

    token = create_access_token(user_id=uid, role="admin")
    # Output in key=value format for sourcing
    print(f"ADMIN_TOKEN={token}")


if __name__ == "__main__":
    asyncio.run(main())
