import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

import packages.common.models
from packages.common.models.base import Base
from apps.api.main import app
from apps.api.core.database import get_db

# Use in-memory SQLite with shared cache for isolated async testing across multiple sessions
TEST_DATABASE_URL = "sqlite+aiosqlite:///file:test_shared_sdr?mode=memory&cache=shared&uri=true"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

from apps.worker.celery_app import celery_app
import apps.worker.tasks.inbound_email
import apps.worker.tasks.crm_sync

# Configure Celery in eager mode for testing without requiring live Redis
celery_app.conf.task_always_eager = True
celery_app.conf.task_eager_propagates = True
apps.worker.tasks.inbound_email.AsyncSessionLocal = TestingSessionLocal
apps.worker.tasks.crm_sync.AsyncSessionLocal = TestingSessionLocal

@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()

    try:
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    except Exception:
        pass

@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
