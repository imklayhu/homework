import json
from pathlib import Path

from app.schemas import AnalysisPayload


def test_demo_result_matches_analysis_contract() -> None:
    fixture = Path(__file__).parents[3] / "samples" / "demo-result.json"
    payload = AnalysisPayload.model_validate(json.loads(fixture.read_text()))

    assert len(payload.chapters) >= 3
    assert len(payload.insights) >= 4
