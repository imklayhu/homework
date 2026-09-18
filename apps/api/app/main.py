import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import init_db
from app.errors import AppError, app_error_handler
from app.routes.health import router as health_router
from app.routes.jobs import router as jobs_router
from app.routes.remixes import router as remixes_router
from app.routes.videos import router as videos_router
from app.routes.admin import router as admin_router
from app.routes.uploads import router as uploads_router
from app.db import engine
from app.models import AnalysisJob
from app.schemas import JobStatus
from app.services.analysis import execute_analysis_job
from sqlmodel import Session, select


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    settings.ensure_directories()
    init_db()
    # Recover jobs left in a transient state by a process/container restart.
    with Session(engine) as session:
        pending = session.exec(select(AnalysisJob).where(AnalysisJob.status.in_((JobStatus.UPLOADED.value, JobStatus.PREPROCESSING.value, JobStatus.UNDERSTANDING.value, JobStatus.ANALYZING.value)))).all()
    recovery_tasks = [asyncio.create_task(execute_analysis_job(job.id, settings)) for job in pending]
    yield
    for task in recovery_tasks:
        task.cancel()


settings = get_settings()
app = FastAPI(title="AI Video Insight Remix API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(jobs_router)
app.include_router(remixes_router)
app.include_router(videos_router)
app.include_router(admin_router)
app.include_router(uploads_router)
app.add_exception_handler(AppError, app_error_handler)
