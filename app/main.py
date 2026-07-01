from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.base import Base, engine
from app.scheduler import scheduler, init_scheduler
from app.dependencies import bp, scanner
from app.routers import api, views
from fastapi.staticfiles import StaticFiles

import logging

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    init_scheduler(bp, scanner)
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)

# Register routes
app.include_router(api.router)
app.include_router(views.router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
