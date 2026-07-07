from collections.abc import AsyncIterator
from urllib.parse import urlsplit

import asyncpg
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.models import *  # noqa: F401,F403  register every model on Base.metadata


async def _ensure_test_database_exists() -> None:
    plain_url = settings.TEST_DATABASE_URL.replace("postgresql+asyncpg://", "")
    db_name = urlsplit("//" + plain_url).path.lstrip("/")
    admin_dsn = "postgresql://" + plain_url.rsplit("/", 1)[0] + "/postgres"

    conn = await asyncpg.connect(admin_dsn)
    try:
        await conn.execute(f'CREATE DATABASE "{db_name}"')
    except asyncpg.DuplicateDatabaseError:
        pass
    finally:
        await conn.close()


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    # Engine is created fresh per test function (not at module import time) so its
    # connection pool binds to *this* test's event loop - pytest-asyncio hands each
    # test function a new loop, and asyncpg connections can't cross loops.
    await _ensure_test_database_exists()
    engine = create_async_engine(settings.TEST_DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def _get_db_override() -> AsyncIterator[AsyncSession]:
        # Mirror app.database.session.get_db's per-request commit/rollback so that
        # multiple HTTP calls within one test see each other's committed writes,
        # exactly as separate requests would in production.
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise

    app.dependency_overrides[get_db] = _get_db_override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
