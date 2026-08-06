import os

# Dummy keys BEFORE importing the app
os.environ.setdefault("BP_API_KEY", "test-key")
os.environ.setdefault("BP_TOKEN", "test-token")

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.sync_tracker import SyncPhase, buy_sync_tracker, sell_sync_tracker
from app.db.base import Base, get_db
from app.main import app


# Fresh in-memory databasejus
@pytest.fixture
async def db_session():
    # StaticPool: force one shared connection so all sessions see the same DB
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)  # Setup
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session  # give the test its session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)  # Teardown: clean slate
    await engine.dispose()


@pytest.fixture
async def client(db_session):
    # Swap the real get_db depencency with our test db_session
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)  # no lifespan, so scheduler never starts
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)  # run automatically for every test.
def reset_trackers():
    # reset state between tests for trackers
    for tracker in (buy_sync_tracker, sell_sync_tracker):
        tracker.phase = SyncPhase.IDLE
        tracker.current = 0
        tracker.total = 0
        tracker.message = ""
        tracker.synced_ids.clear()
