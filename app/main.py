from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.core.logging import configure_logging
from app.api.health import router as health_router
from app.api.v1.chat import router as chat_router
from app.api.v1.models import router as models_router, _models_client
from app.services.proxy.base import http_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.debug)
    yield
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

app.include_router(health_router)
app.include_router(chat_router, prefix="/v1")
app.include_router(models_router, prefix="/v1")
