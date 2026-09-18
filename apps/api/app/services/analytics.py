import json
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from statistics import median
from sqlmodel import Session, select

from app.models import AnalysisJob, AnalyticsEvent, RemixJob, Video


def record_event(session: Session, name: str, properties: dict | None = None, session_id: str | None = None) -> None:
    safe = {key: value for key, value in (properties or {}).items() if isinstance(value, (str, int, float, bool)) or value is None}
    session.add(AnalyticsEvent(name=name, properties_json=json.dumps(safe, ensure_ascii=False), session_id=session_id))


def _percentiles(values: list[float]) -> dict[str, float]:
    if not values:
        return {"avg": 0, "p50": 0, "p95": 0}
    ordered = sorted(values)
    return {"avg": round(sum(ordered) / len(ordered), 2), "p50": round(median(ordered), 2), "p95": round(ordered[min(len(ordered) - 1, int(len(ordered) * .95))], 2)}


def build_metrics(session: Session, days: int = 30) -> dict:
    days = max(1, min(days, 90))
    since = datetime.now(UTC) - timedelta(days=days)
    videos = session.exec(select(Video).where(Video.created_at >= since)).all()
    jobs = session.exec(select(AnalysisJob).where(AnalysisJob.created_at >= since)).all()
    remixes = session.exec(select(RemixJob).where(RemixJob.created_at >= since)).all()
    events = session.exec(select(AnalyticsEvent).where(AnalyticsEvent.created_at >= since)).all()
    event_counts = Counter(event.name for event in events)
    completed = [job for job in jobs if job.status == "completed"]
    failed = [job for job in jobs if job.status == "failed"]
    durations = [(job.updated_at - job.created_at).total_seconds() for job in jobs if job.updated_at and job.updated_at >= job.created_at and job.status in {"completed", "failed"}]
    errors = Counter(job.error_code or "UNKNOWN" for job in failed)
    daily = defaultdict(lambda: {"videos": 0, "jobs": 0, "completed": 0, "failed": 0, "cost": 0.0})
    for video in videos:
        daily[video.created_at.date().isoformat()]["videos"] += 1
    for job in jobs:
        bucket = daily[job.created_at.date().isoformat()]
        bucket["jobs"] += 1
        bucket[job.status] = bucket.get(job.status, 0) + 1
        bucket["cost"] += job.estimated_cost or 0
    usage_tokens = 0
    for job in completed:
        if job.provider_usage_json:
            try:
                usage = json.loads(job.provider_usage_json)
                usage_tokens += int(usage.get("total_tokens", 0) or 0)
            except (TypeError, ValueError, json.JSONDecodeError):
                pass
    return {
        "window_days": days,
        "total_events": sum(event_counts.values()), "events": dict(event_counts),
        "usage": {"videos": len(videos), "duration_ms": sum(v.duration_ms for v in videos), "bytes": sum(v.size_bytes for v in videos)},
        "jobs": {"total": len(jobs), "completed": len(completed), "failed": len(failed), "in_progress": len(jobs) - len(completed) - len(failed), "completion_rate": round(len(completed) / len(jobs) * 100, 1) if jobs else 0, "retry_count": event_counts.get("analysis_retried", 0)},
        "performance": {"analysis_seconds": _percentiles(durations)},
        "failures": {"by_code": dict(errors), "recent": [{"id": j.id, "stage": j.failed_stage, "code": j.error_code, "message": j.error_message, "created_at": j.created_at.isoformat()} for j in sorted(failed, key=lambda x: x.created_at, reverse=True)[:10]]},
        "model": {"calls": len(completed), "total_tokens": usage_tokens, "estimated_cost": round(sum(j.estimated_cost or 0 for j in completed), 6), "average_cost": round(sum(j.estimated_cost or 0 for j in completed) / len(completed), 6) if completed else 0},
        "remix": {"total": len(remixes), "completed": sum(r.status == "completed" for r in remixes), "failed": sum(r.status == "failed" for r in remixes), "completion_rate": round(sum(r.status == "completed" for r in remixes) / len(remixes) * 100, 1) if remixes else 0, "duration_ms": sum(r.duration_ms or 0 for r in remixes)},
        "daily": [{"date": day, **values} for day, values in sorted(daily.items())],
    }
