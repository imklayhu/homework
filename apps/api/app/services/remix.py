import json
import shutil
import subprocess
from pathlib import Path

from sqlmodel import Session, select

from app.errors import AppError
from app.models import AnalysisJob, AnalysisResult, RemixJob, Video, utc_now
from app.schemas import AnalysisPayload, Insight, RemixStatus
from app.services.media import probe_video
from app.db import engine


def resolve_segments(session: Session, video_id: str, insight_ids: list[str]) -> list[Insight]:
    if len(insight_ids) != len(set(insight_ids)):
        raise AppError("INVALID_INSIGHT", "不能重复选择同一个观点。")
    job = session.exec(
        select(AnalysisJob)
        .where(AnalysisJob.video_id == video_id)
        .where(AnalysisJob.status == "completed")
        .order_by(AnalysisJob.updated_at.desc())
    ).first()
    if job is None:
        raise AppError("RESULT_UNAVAILABLE", "该视频还没有可用的分析结果。", 409)
    result = session.exec(
        select(AnalysisResult).where(AnalysisResult.job_id == job.id)
    ).first()
    if result is None:
        raise AppError("RESULT_UNAVAILABLE", "该视频还没有可用的分析结果。", 409)
    payload = AnalysisPayload.model_validate_json(result.insights_json)
    by_id = {insight.id: insight for insight in payload.insights}
    try:
        segments = [by_id[insight_id] for insight_id in insight_ids]
    except KeyError as exc:
        raise AppError("INVALID_INSIGHT", "选择的观点不属于该视频。") from exc
    if sum(item.end_ms - item.start_ms for item in segments) > 180_000:
        raise AppError("REMIX_TOO_LONG", "Remix 总时长不能超过 3 分钟。")
    return segments


def render_remix(remix_id: str, session: Session, data_dir: Path) -> None:
    remix = session.get(RemixJob, remix_id)
    if remix is None:
        return
    video = session.get(Video, remix.video_id)
    if video is None:
        return
    temp_dir = data_dir / "tmp" / remix.id
    output_dir = data_dir / "remixes" / remix.id
    try:
        remix.status = RemixStatus.RENDERING.value
        remix.updated_at = utc_now()
        session.add(remix); session.commit()
        insight_ids = json.loads(remix.selected_segments_json)
        segments = resolve_segments(session, video.id, insight_ids)
        source = (data_dir / video.storage_key).resolve()
        if not source.is_relative_to(data_dir.resolve()) or not source.is_file():
            raise AppError("VIDEO_NOT_FOUND", "源视频不存在或已经过期。", 404)
        temp_dir.mkdir(parents=True, exist_ok=True)
        clip_paths: list[Path] = []
        for index, segment in enumerate(segments):
            clip = temp_dir / f"clip-{index:02d}.mp4"
            command = [
                "ffmpeg", "-y", "-ss", str(segment.start_ms / 1000), "-i", str(source),
                "-t", str((segment.end_ms - segment.start_ms) / 1000),
                "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-ar", "48000", "-movflags", "+faststart", str(clip),
            ]
            subprocess.run(command, check=True, capture_output=True, text=True, timeout=300)
            clip_paths.append(clip)
        concat_file = temp_dir / "concat.txt"
        concat_file.write_text("".join(f"file '{path.name}'\n" for path in clip_paths))
        output_dir.mkdir(parents=True, exist_ok=True)
        output = output_dir / "remix.mp4"
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "1", "-i", str(concat_file),
             "-c", "copy", "-movflags", "+faststart", str(output)],
            check=True, capture_output=True, text=True, timeout=300,
        )
        metadata = probe_video(output)
        remix.status = RemixStatus.COMPLETED.value
        remix.output_storage_key = output.relative_to(data_dir).as_posix()
        remix.duration_ms = metadata.duration_ms
        remix.error_code = None
        remix.error_message = None
    except (AppError, subprocess.SubprocessError) as exc:
        remix.status = RemixStatus.FAILED.value
        remix.error_code = exc.code if isinstance(exc, AppError) else "REMIX_RENDER_FAILED"
        remix.error_message = exc.message if isinstance(exc, AppError) else "视频生成失败，请重试。"
        remix.error_detail = None
    finally:
        remix.updated_at = utc_now()
        session.add(remix); session.commit()
        shutil.rmtree(temp_dir, ignore_errors=True)


def execute_remix_job(remix_id: str, data_dir: Path) -> None:
    with Session(engine) as session:
        render_remix(remix_id, session, data_dir)
