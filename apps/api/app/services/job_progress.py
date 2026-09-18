from __future__ import annotations

from sqlmodel import Session, select

from app.models import AnalysisJob, AnalysisJobLog, utc_now


VALID_LEVELS = {"info", "warning", "error"}


def _commit_job(session: Session, job: AnalysisJob) -> None:
    job.updated_at = utc_now()
    session.add(job)
    session.commit()
    session.refresh(job)


def append_job_log(
    session: Session,
    job: AnalysisJob,
    message: str,
    level: str = "info",
    stage: str = "understanding",
) -> AnalysisJobLog:
    if level not in VALID_LEVELS:
        raise ValueError(f"Unsupported progress log level: {level}")
    log = AnalysisJobLog(job_id=job.id, stage=stage, level=level, message=message)
    job.progress_message = message
    session.add(log)
    _commit_job(session, job)
    session.refresh(log)
    return log


def initialize_progress(
    session: Session,
    job: AnalysisJob,
    duration_ms: int,
    segment_ms: int,
) -> None:
    total = max(1, (duration_ms + segment_ms - 1) // segment_ms)
    job.progress_current = 0
    job.progress_total = total
    job.progress_percent = 0
    job.progress_message = f"准备分析视频，共 {total} 个片段"
    session.add(AnalysisJobLog(job_id=job.id, stage="understanding", message=job.progress_message))
    _commit_job(session, job)


def set_progress_message(
    session: Session,
    job: AnalysisJob,
    message: str,
    level: str = "info",
) -> None:
    append_job_log(session, job, message, level=level)


def complete_segment(session: Session, job: AnalysisJob, segment_number: int) -> None:
    current = max(job.progress_current, min(segment_number, job.progress_total))
    job.progress_current = current
    job.progress_percent = min(100, round(current / job.progress_total * 100)) if job.progress_total else 0
    message = f"第 {current}/{job.progress_total} 个片段理解完成"
    job.progress_message = message
    session.add(AnalysisJobLog(job_id=job.id, stage="understanding", message=message))
    _commit_job(session, job)


def recent_logs(session: Session, job_id: str, limit: int = 20) -> list[AnalysisJobLog]:
    bounded_limit = max(1, min(limit, 20))
    rows = session.exec(
        select(AnalysisJobLog)
        .where(AnalysisJobLog.job_id == job_id)
        .order_by(AnalysisJobLog.created_at.desc(), AnalysisJobLog.id.desc())
        .limit(bounded_limit)
    ).all()
    return list(reversed(rows))
