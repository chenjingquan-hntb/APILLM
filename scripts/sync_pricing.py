"""
从 newcli /api/pricing 自动同步模型定价到 ModelConfig 表。
运行: python scripts/sync_pricing.py
"""
import asyncio
from app.services.pricing_sync import sync_pricing_to_db
from app.db.base import async_session_factory


async def main():
    result = await sync_pricing_to_db(async_session_factory)
    print(f"完成！新建: {result['created']}  更新: {result['updated']}  合计: {result['total']}")


if __name__ == "__main__":
    asyncio.run(main())
