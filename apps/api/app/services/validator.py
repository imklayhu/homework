from dataclasses import dataclass

from app.errors import AppError
from app.schemas import AnalysisPayload


MIN_INSIGHT_DURATION_MS = 5_000
MAX_INSIGHT_DURATION_MS = 120_000


@dataclass(frozen=True)
class ValidatedAnalysis:
    payload: AnalysisPayload
    warnings: list[str]


def normalize_range(
    start_ms: int, end_ms: int, duration_ms: int, padding_ms: int = 1_000
) -> tuple[int, int]:
    return max(0, start_ms - padding_ms), min(duration_ms, end_ms + padding_ms)


def ensure_minimum_duration(
    start_ms: int, end_ms: int, duration_ms: int, minimum_ms: int = MIN_INSIGHT_DURATION_MS
) -> tuple[int, int]:
    current_ms = end_ms - start_ms
    if current_ms >= minimum_ms:
        return start_ms, end_ms

    missing_ms = minimum_ms - current_ms
    expanded_end_ms = min(duration_ms, end_ms + missing_ms)
    missing_ms -= expanded_end_ms - end_ms
    expanded_start_ms = max(0, start_ms - missing_ms)
    return expanded_start_ms, expanded_end_ms


def validate_and_normalize(
    payload: AnalysisPayload, duration_ms: int, padding_ms: int = 1_000
) -> ValidatedAnalysis:
    result = payload.model_copy(deep=True)
    ids = [item.id for item in result.chapters] + [item.id for item in result.insights]
    if len(ids) != len(set(ids)):
        raise AppError("INVALID_MODEL_OUTPUT", "模型返回了重复的章节或观点。", 502)

    warnings: list[str] = []
    result.chapters.sort(key=lambda item: item.start_ms)
    for item in [*result.chapters, *result.insights]:
        if item.start_ms >= duration_ms:
            raise AppError("INVALID_MODEL_OUTPUT", "模型返回了超出视频范围的时间点。", 502)
        item.end_ms = min(item.end_ms, duration_ms)
        if item.start_ms >= item.end_ms:
            raise AppError("INVALID_MODEL_OUTPUT", "模型返回了无效的时间范围。", 502)

    for insight in result.insights:
        insight.start_ms, insight.end_ms = ensure_minimum_duration(
            insight.start_ms, insight.end_ms, duration_ms
        )
        insight_duration_ms = insight.end_ms - insight.start_ms
        if insight_duration_ms > MAX_INSIGHT_DURATION_MS:
            raise AppError(
                "INVALID_MODEL_OUTPUT",
                "模型返回的观点片段时长不符合要求。",
                502,
            )
        start_ms, end_ms = normalize_range(
            insight.start_ms, insight.end_ms, duration_ms, padding_ms
        )
        insight.start_ms = start_ms
        insight.end_ms = end_ms

    ordered = sorted(result.insights, key=lambda item: item.start_ms)
    for previous, current in zip(ordered, ordered[1:]):
        overlap = min(previous.end_ms, current.end_ms) - max(previous.start_ms, current.start_ms)
        shorter = min(previous.end_ms - previous.start_ms, current.end_ms - current.start_ms)
        if overlap > 0 and shorter > 0 and overlap / shorter >= 0.7:
            warnings.append(f"{previous.id} 与 {current.id} 高度重叠")
    return ValidatedAnalysis(payload=result, warnings=warnings)
