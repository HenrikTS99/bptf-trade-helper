from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.base import Base, engine
from app.scheduler import scheduler, init_scheduler
from app.dependencies import bp, scanner
from app.routers import api


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    init_scheduler(bp, scanner)
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)
app.include_router(api.router)
