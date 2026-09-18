import json

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlmodel import Session, select

from app.db import get_session
from app.config import Settings, get_settings
from app.errors import AppError
from app.models import AnalysisJob, AnalysisResult
from app.schemas import AnalysisJobLogRead, AnalysisJobRead, AnalysisPayload, JobStatus
from app.services.analysis import execute_analysis_job
from app.services.job_progress import append_job_log, recent_logs


router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def serialize_job(job: AnalysisJob, session: Session) -> AnalysisJobRead:
    usage = json.loads(job.provider_usage_json) if job.provider_usage_json else None
    return AnalysisJobRead(
        id=job.id,
        video_id=job.video_id,
        status=JobStatus(job.status),
        current_stage=JobStatus(job.current_stage),
        error_code=job.error_code,
        error_message=job.error_message,
        provider_usage=usage,
        estimated_cost=job.estimated_cost,
        progress_current=job.progress_current,
        progress_total=job.progress_total,
        progress_percent=job.progress_percent,
        progress_message=job.progress_message,
        logs=[
            AnalysisJobLogRead(
                id=log.id,
                stage=log.stage,
                level=log.level,
                message=log.message,
                created_at=log.created_at,
            )
            for log in recent_logs(session, job.id)
        ],
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get("/{job_id}", response_model=AnalysisJobRead)
def get_job(job_id: str, session: Session = Depends(get_session)) -> AnalysisJobRead:
    job = session.get(AnalysisJob, job_id)
    if job is None:
        raise AppError("JOB_NOT_FOUND", "分析任务不存在。", 404)
    return serialize_job(job, session)


@router.get("/{job_id}/result", response_model=AnalysisPayload)
def get_result(job_id: str, session: Session = Depends(get_session)) -> AnalysisPayload:
    job = session.get(AnalysisJob, job_id)
    if job is None:
        raise AppError("JOB_NOT_FOUND", "分析任务不存在。", 404)
    if job.status != JobStatus.COMPLETED.value:
        raise AppError("JOB_NOT_COMPLETED", "分析尚未完成。", 409)
    result = session.exec(
        select(AnalysisResult).where(AnalysisResult.job_id == job_id)
    ).first()
    if result is None:
        raise AppError("RESULT_UNAVAILABLE", "分析结果暂不可用。", 500)
    return AnalysisPayload.model_validate_json(result.insights_json)


@router.post("/{job_id}/retry", response_model=AnalysisJobRead, status_code=202)
def retry_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AnalysisJobRead:
    job = session.get(AnalysisJob, job_id)
    if job is None:
        raise AppError("JOB_NOT_FOUND", "分析任务不存在。", 404)
    if job.status != JobStatus.FAILED.value:
        raise AppError("JOB_NOT_RETRYABLE", "只有失败任务可以重试。", 409)
    job.status = JobStatus.UPLOADED.value
    job.current_stage = JobStatus.UPLOADED.value
    job.error_code = None
    job.error_message = None
    job.progress_current = 0
    job.progress_total = 0
    job.progress_percent = 0
    job.progress_message = "重新开始视频分析"
    session.add(job)
    session.commit()
    session.refresh(job)
    append_job_log(session, job, "重新开始视频分析")
    background_tasks.add_task(execute_analysis_job, job.id, settings)
    return serialize_job(job, session)
