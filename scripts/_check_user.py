import asyncio
from app.db.base import async_session_factory
from app.db.models import Upstream
from sqlalchemy import select, update

async def main():
    async with async_session_factory() as s:
        r = await s.execute(select(Upstream))
        ups = r.scalars().all()
        for u in ups:
            if not u.is_enabled:
                print(f"启用上游: {u.name} (id={u.id})")
                u.is_enabled = True
        await s.commit()
        print("完成")

asyncio.run(main())
