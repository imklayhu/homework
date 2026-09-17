#!/usr/bin/env python3
import argparse
import asyncio
import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from app.config import get_settings  # noqa: E402
from app.services.analysis import video_data_url  # noqa: E402
from app.services.bailian import BailianVideoAdapter  # noqa: E402
from app.services.cost import Pricing, estimate_cost  # noqa: E402
from app.services.media import probe_video  # noqa: E402
from app.services.validator import validate_and_normalize  # noqa: E402


async def analyze(path: Path, output: Path) -> None:
    settings = get_settings()
    if settings.on_demand_api_key is None or not settings.on_demand_base_url:
        raise SystemExit("ON_DEMAND model configuration is missing")
    metadata = probe_video(path)
    adapter = BailianVideoAdapter(
        settings.on_demand_base_url,
        settings.on_demand_api_key.get_secret_value(),
        settings.video_understanding_model,
    )
    started = time.monotonic()
    result = await adapter.analyze(video_data_url(path, "video/mp4"), metadata.duration_ms)
    validated = validate_and_normalize(result.payload, metadata.duration_ms)
    elapsed = time.monotonic() - started
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(validated.payload.model_dump_json(indent=2), encoding="utf-8")
    print(json.dumps({
        "status": "completed",
        "duration_ms": metadata.duration_ms,
        "elapsed_seconds": round(elapsed, 2),
        "model": result.model,
        "chapters": len(validated.payload.chapters),
        "insights": len(validated.payload.insights),
        "usage": result.usage,
        "estimated_cost_cny": estimate_cost(result.usage, Pricing(0.8, 2.7)),
        "output": str(output),
    }, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("video", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "data/smoke/result.json")
    args = parser.parse_args()
    asyncio.run(analyze(args.video.resolve(), args.output.resolve()))


if __name__ == "__main__":
    main()
