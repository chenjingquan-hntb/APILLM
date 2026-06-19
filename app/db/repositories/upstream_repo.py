from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Upstream
from app.db.repositories.base import BaseRepository


class UpstreamRepository(BaseRepository[Upstream]):
    def __init__(self, session: AsyncSession):
        super().__init__(Upstream, session)

    async def get_enabled(self) -> list[Upstream]:
        return await self.list(is_enabled=True)
