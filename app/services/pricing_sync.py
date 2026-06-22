"""
从 newcli /api/pricing 同步模型定价到 ModelConfig 表。
后台定时任务 + 手动触发共用此模块。
"""
import asyncio
from datetime import datetime, UTC
import httpx
from sqlalchemy import select
from app.core.logging import logger
from app.db.models import ModelConfig

PRICING_API = "https://business.newcli.com/api/pricing"
DEFAULT_SYNC_INTERVAL = 3600  # 每小时


async def sync_pricing_to_db(session_factory) -> dict:
    """从 PRICING_API 抓取定价，写入 ModelConfig 表。返回统计信息。"""
    logger.info("pricing_sync_started")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(PRICING_API)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.error("pricing_sync_fetch_failed", error=str(e))
        raise

    models = data.get("data", [])
    group_ratio = data.get("group_ratio", {})
    default_gr = group_ratio.get("default", 1.0)
    price_per_unit = data.get("price", 1.0)
    quota_per_unit = data.get("quota_per_unit", 500000)
    # newcli 标价 $ 实际为人民币 1:1，不做汇率换算
    cny_per_unit = price_per_unit  # $1 = ¥1

    # 基础价格: CNY / 1K token (default 分组)
    base_cny_per_1k = (cny_per_unit / quota_per_unit) * 1000

    now = datetime.now(UTC)
    created = 0
    updated = 0

    async with session_factory() as session:
        # 批量加载所有现有配置，避免 N+1 查询
        existing_result = await session.execute(select(ModelConfig))
        existing_map: dict[str, ModelConfig] = {
            mc.model_id: mc for mc in existing_result.scalars().all()
        }

        for m in models:
            model_id = m.get("model_name", "")
            if not model_id:
                continue
            mr = m.get("model_ratio", 1.0)
            cr = m.get("completion_ratio", 1.0)
            prompt_cny = round(base_cny_per_1k * mr * default_gr / 1000, 10)
            completion_cny = round(base_cny_per_1k * cr * default_gr / 1000, 10)
            if prompt_cny == 0 and completion_cny == 0:
                continue

            mc = existing_map.get(model_id)
            if mc:
                mc.manual_prompt_price = prompt_cny
                mc.manual_completion_price = completion_cny
                mc.is_enabled = True
                mc.updated_at = now
                updated += 1
            else:
                mc = ModelConfig(
                    model_id=model_id,
                    manual_prompt_price=prompt_cny,
                    manual_completion_price=completion_cny,
                    is_enabled=True,
                )
                session.add(mc)
                created += 1

        await session.commit()

    result = {"created": created, "updated": updated, "total": created + updated}
    logger.info("pricing_sync_completed", **result)
    return result


async def run_pricing_sync_loop(session_factory) -> None:
    """后台循环：每小时自动同步一次 newcli 定价。"""
    logger.info("pricing_sync_loop_started", interval=DEFAULT_SYNC_INTERVAL)
    while True:
        try:
            await sync_pricing_to_db(session_factory)
        except asyncio.CancelledError:
            logger.info("pricing_sync_loop_cancelled")
            return
        except Exception:
            logger.error("pricing_sync_loop_error", exc_info=True)
        await asyncio.sleep(DEFAULT_SYNC_INTERVAL)
