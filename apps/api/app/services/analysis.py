import asyncio
import base64
import json
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from sqlmodel import Session, select

from app.config import Settings
from app.db import engine
from app.errors import AppError
from app.models import AnalysisJob, AnalysisResult, Video, utc_now
from app.schemas import AnalysisPayload, JobStatus
from app.services.bailian import ModelAnalysisResult, ProgressCallback
from app.services.bailian import BailianVideoAdapter
from app.services.capacity import job_capacity
from app.services.analytics import record_event
from app.services.cost import Pricing, estimate_cost
from app.services.media import create_analysis_proxy
from app.services.validator import validate_and_normalize


class AnalysisAdapter(Protocol):
    async def analyze(
        self,
        video_url: str,
        duration_ms: int,
        on_progress: ProgressCallback | None = None,
    ) -> ModelAnalysisResult:
        raise NotImplementedError


FALLBACK_ERROR_CODES = {
    "MODEL_AUTH_FAILED",
    "MODEL_REQUEST_FAILED",
    "MODEL_TIMEOUT",
    "MODEL_UNAVAILABLE",
    "INVALID_MODEL_OUTPUT",
}


class FallbackAnalysisAdapter:
    def __init__(self, primary: AnalysisAdapter, secondary: AnalysisAdapter) -> None:
        self.primary = primary
        self.secondary = secondary

    async def analyze(
        self,
        video_url: str,
        duration_ms: int,
        on_progress: ProgressCallback | None = None,
    ) -> ModelAnalysisResult:
        try:
            return await self.primary.analyze(video_url, duration_ms, on_progress=on_progress)
        except AppError as exc:
            if exc.code not in FALLBACK_ERROR_CODES:
                raise
            return await self.secondary.analyze(video_url, duration_ms, on_progress=on_progress)


def build_analysis_adapter(settings: Settings) -> AnalysisAdapter | None:
    primary: AnalysisAdapter | None = None
    secondary: AnalysisAdapter | None = None
    if settings.on_demand_api_key is not None and settings.on_demand_base_url:
        primary = BailianVideoAdapter(
            settings.on_demand_base_url,
            settings.on_demand_api_key.get_secret_value(),
            settings.video_understanding_model,
        )
    if settings.bailian_api_key is not None and settings.bailian_base_url:
        secondary = BailianVideoAdapter(
            settings.bailian_base_url,
            settings.bailian_api_key.get_secret_value(),
            settings.workspace_video_model,
        )
    if primary is not None and secondary is not None:
        return FallbackAnalysisAdapter(primary, secondary)
    return primary or secondary


def video_data_url(path: Path, mime_type: str) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def update_stage(session: Session, job: AnalysisJob, status: JobStatus) -> None:
    job.status = status.value
    job.current_stage = status.value
    job.updated_at = utc_now()
    session.add(job)
    record_event(session, "analysis_stage_changed", {"job_id": job.id, "stage": status.value})
    session.commit()


async def analyze_in_segments(
    source: Path,
    duration_ms: int,
    data_dir: Path,
    job_id: str,
    adapter: AnalysisAdapter,
    session: Session | None = None,
    job: AnalysisJob | None = None,
) -> tuple[ModelAnalysisResult, Path]:
    # Keep inline base64 video requests small enough for model gateways to
    # ingest reliably. A three-minute proxy is ~9 MB (12+ MB after base64)
    # for ordinary lecture video and repeatedly times out upstream.
    segment_ms = 30_000
    results: list[ModelAnalysisResult] = []
    proxies: list[Path] = []
    if session is not None and job is not None:
        from app.services.job_progress import initialize_progress

        initialize_progress(session, job, duration_ms, segment_ms)

    async def on_progress(level: str, message: str) -> None:
        if session is not None and job is not None:
            from app.services.job_progress import set_progress_message

            set_progress_message(session, job, message, level=level)

    try:
        for index, start_ms in enumerate(range(0, duration_ms, segment_ms)):
            length_ms = min(segment_ms, duration_ms - start_ms)
            proxy = data_dir / "tmp" / f"analysis-{job_id}-{index}-{uuid4().hex}.mp4"
            proxies.append(proxy)
            if session is not None and job is not None:
                from app.services.job_progress import set_progress_message

                set_progress_message(
                    session,
                    job,
                    f"正在生成第 {index + 1}/{job.progress_total} 个分析片段",
                )
            # ffmpeg is a blocking subprocess; keep it off the event loop so
            # health checks, job polling, and other requests remain responsive
            # while long videos are being transcoded.
            await asyncio.to_thread(
                create_analysis_proxy,
                source,
                proxy,
                start_ms / 1000,
                length_ms / 1000,
            )
            if session is not None and job is not None:
                set_progress_message(
                    session,
                    job,
                    f"正在理解第 {index + 1}/{job.progress_total} 个片段（{_format_time(start_ms)}–{_format_time(start_ms + length_ms)}）",
                )
            results.append(
                await adapter.analyze(
                    video_data_url(proxy, "video/mp4"),
                    length_ms,
                    on_progress=on_progress,
                )
            )
            if session is not None and job is not None:
                from app.services.job_progress import complete_segment

                complete_segment(session, job, index + 1)

        chapters = []
        insights = []
        for index, result in enumerate(results):
            offset = index * segment_ms
            chapters.extend(item.model_copy(update={"id": f"{item.id}-s{index}" if len(results) > 1 else item.id, "start_ms": item.start_ms + offset, "end_ms": item.end_ms + offset}) for item in result.payload.chapters)
            insights.extend(item.model_copy(update={"id": f"{item.id}-s{index}" if len(results) > 1 else item.id, "start_ms": item.start_ms + offset, "end_ms": item.end_ms + offset}) for item in result.payload.insights)
        chapters = sorted(chapters, key=lambda item: item.start_ms)[:12]
        insights = sorted(insights, key=lambda item: (-item.confidence, item.start_ms))[:12]
        merged = AnalysisPayload(summary="\n".join(result.payload.summary for result in results), chapters=chapters, insights=insights)
        usage = {key: sum(item.usage.get(key, 0) for item in results if isinstance(item.usage.get(key), int)) for key in ("prompt_tokens", "completion_tokens")}
        return ModelAnalysisResult(merged, usage, results[0].model, results[0].prompt_version), proxies[0]
    finally:
        for proxy in proxies:
            proxy.unlink(missing_ok=True)


def _format_time(milliseconds: int) -> str:
    total_seconds = max(0, milliseconds // 1000)
    return f"{total_seconds // 60:02d}:{total_seconds % 60:02d}"


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
        model_result, _ = await analyze_in_segments(
            source,
            video.duration_ms,
            data_dir,
            job.id,
            adapter,
            session=session,
            job=job,
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
        from app.services.job_progress import set_progress_message

        set_progress_message(session, job, exc.message, level="error")
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
        from app.services.job_progress import set_progress_message

        set_progress_message(session, job, "视频分析失败，请重试。", level="error")
        session.commit()


async def execute_analysis_job(job_id: str, settings: Settings) -> None:
    async with job_capacity():
        adapter = build_analysis_adapter(settings)
        if adapter is None:
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
        with Session(engine) as session:
            await run_analysis(job_id, session, settings.data_dir, adapter)
