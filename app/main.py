import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.logging import configure_logging, logger
from app.db.base import async_session_factory
from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.admin import router as admin_router
from app.api.v1.chat import router as chat_router
from app.api.v1.models import router as models_router, _models_client
from app.services.proxy.base import http_client
from app.services.redis import init_redis, close_redis
from app.services.price_fetcher import run_price_fetch_loop, close_price_client
from app.services.health_checker import run_health_loop, close_health_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.debug)
    await init_redis()
    tasks: list[asyncio.Task] = []
    tasks.append(asyncio.create_task(run_price_fetch_loop(async_session_factory)))
    tasks.append(asyncio.create_task(run_health_loop(async_session_factory)))
    try:
        yield
    finally:
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        await close_health_client()
        await close_price_client()
        await close_redis()
        await http_client.aclose()
        await _models_client.aclose()


app = FastAPI(
    title="LLM Relay",
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url=None,
)

# CORS — 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(chat_router, prefix="/v1")
app.include_router(models_router, prefix="/v1")

# 静态文件 — 托管前端 Dashboard
web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Web")
if os.path.isdir(web_dir):
    app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")
