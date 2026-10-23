from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from concurrency_lab.core.config import Settings
from concurrency_lab.db.session import create_engine
from concurrency_lab.models.marker import LabMarker


async def test_mysql_session_roundtrip():
    engine = create_engine(Settings())
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session:
            async with session.begin():
                marker = LabMarker()
                session.add(marker)
                await session.flush()
                marker_id = marker.id
            assert (
                await session.scalar(select(LabMarker.id).where(LabMarker.id == marker_id))
            ) == marker_id
            await session.delete(marker)
            await session.commit()
    finally:
        await engine.dispose()
