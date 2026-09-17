import base64
import json
from pathlib import Path
from typing import Protocol

from sqlmodel import Session, select

from app.config import Settings
from app.db import engine
from app.errors import AppError
from app.models import AnalysisJob, AnalysisResult, Video, utc_now
from app.schemas import JobStatus
from app.services.bailian import ModelAnalysisResult
from app.services.bailian import BailianVideoAdapter
from app.services.cost import Pricing, estimate_cost
from app.services.validator import validate_and_normalize


class AnalysisAdapter(Protocol):
    async def analyze(self, video_url: str, duration_ms: int) -> ModelAnalysisResult:
        raise NotImplementedError


def video_data_url(path: Path, mime_type: str) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def update_stage(session: Session, job: AnalysisJob, status: JobStatus) -> None:
    job.status = status.value
    job.current_stage = status.value
    job.updated_at = utc_now()
    session.add(job)
    session.commit()


async def run_analysis(
    job_id: str,
    session: Session,
    data_dir: Path,
    adapter: AnalysisAdapter,
) -> None:
    job = session.get(AnalysisJob, job_id)
    if job is None or job.status == JobStatus.COMPLETED.value:
        return
    video = session.get(Video, job.video_id)
    if video is None:
        return

    try:
        update_stage(session, job, JobStatus.PREPROCESSING)
        source = (data_dir / video.storage_key).resolve()
        if not source.is_relative_to(data_dir.resolve()) or not source.is_file():
            raise AppError("VIDEO_NOT_FOUND", "视频不存在或已经过期。", 404)

        update_stage(session, job, JobStatus.UNDERSTANDING)
        model_result = await adapter.analyze(
            video_data_url(source, video.mime_type), video.duration_ms
        )

        update_stage(session, job, JobStatus.ANALYZING)
        validated = validate_and_normalize(model_result.payload, video.duration_ms)
        existing = session.exec(
            select(AnalysisResult).where(AnalysisResult.job_id == job.id)
        ).first()
        if existing is not None:
            session.delete(existing)
        result = AnalysisResult(
            job_id=job.id,
            insights_json=validated.payload.model_dump_json(),
            visual_observations_json=json.dumps(
                {"warnings": validated.warnings}, ensure_ascii=False
            ),
            prompt_version=model_result.prompt_version,
            model_version=model_result.model,
        )
        job.provider_usage_json = json.dumps(model_result.usage, ensure_ascii=False)
        job.estimated_cost = estimate_cost(model_result.usage, Pricing(0.8, 2.7))
        job.error_code = None
        job.error_message = None
        job.failed_stage = None
        session.add(result)
        session.add(job)
        session.commit()
        update_stage(session, job, JobStatus.COMPLETED)
    except AppError as exc:
        failed_stage = job.current_stage
        job.status = JobStatus.FAILED.value
        job.failed_stage = failed_stage
        job.error_code = exc.code
        job.error_message = exc.message
        job.error_detail = None
        job.updated_at = utc_now()
        session.add(job)
        session.commit()
    except Exception:
        failed_stage = job.current_stage
        job.status = JobStatus.FAILED.value
        job.failed_stage = failed_stage
        job.error_code = "ANALYSIS_FAILED"
        job.error_message = "视频分析失败，请重试。"
        job.error_detail = None
        job.updated_at = utc_now()
        session.add(job)
        session.commit()


async def execute_analysis_job(job_id: str, settings: Settings) -> None:
    if settings.on_demand_api_key is None or not settings.on_demand_base_url:
        with Session(engine) as session:
            job = session.get(AnalysisJob, job_id)
            if job is not None:
                job.status = JobStatus.FAILED.value
                job.current_stage = JobStatus.FAILED.value
                job.failed_stage = JobStatus.UPLOADED.value
                job.error_code = "MODEL_NOT_CONFIGURED"
                job.error_message = "模型服务尚未配置。"
                session.add(job)
                session.commit()
        return
    adapter = BailianVideoAdapter(
        settings.on_demand_base_url,
        settings.on_demand_api_key.get_secret_value(),
        settings.video_understanding_model,
    )
    with Session(engine) as session:
        await run_analysis(job_id, session, settings.data_dir, adapter)
