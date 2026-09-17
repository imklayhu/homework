import json
from pathlib import Path

import httpx
import pytest

from app.errors import AppError
from app.services.bailian import BailianVideoAdapter


FIXTURE_DIR = Path(__file__).parent / "fixtures"


@pytest.mark.asyncio
async def test_analyze_sends_video_and_parses_schema() -> None:
    response_data = json.loads((FIXTURE_DIR / "qwen-response.json").read_text())
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        assert request.headers["authorization"] == "Bearer secret"
        return httpx.Response(200, json=response_data)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = BailianVideoAdapter(
            base_url="https://example.invalid/v1",
            api_key="secret",
            model="qwen3-vl-flash",
            client=client,
        )
        result = await adapter.analyze("https://example.com/video.mp4", 4_000)

    content = captured["messages"][1]["content"]
    assert content[0]["type"] == "video_url"
    assert captured["response_format"]["type"] == "json_schema"
    assert captured["response_format"]["json_schema"]["strict"] is True
    assert result.payload.insights[0].id == "insight_01"
    assert result.usage["total_tokens"] == 1180
    assert result.prompt_version == "qwen-video-v1"


@pytest.mark.asyncio
async def test_authentication_error_is_not_retried() -> None:
    attempts = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(401, json={"error": {"message": "bad key"}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = BailianVideoAdapter("https://example.invalid/v1", "secret", client=client)
        with pytest.raises(AppError, match="MODEL_AUTH_FAILED"):
            await adapter.analyze("https://example.com/video.mp4", 4_000)

    assert attempts == 1


@pytest.mark.asyncio
async def test_server_error_retries_twice() -> None:
    attempts = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(503, json={"error": {"message": "unavailable"}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = BailianVideoAdapter(
            "https://example.invalid/v1", "secret", client=client, sleep=lambda _: None
        )
        with pytest.raises(AppError, match="MODEL_UNAVAILABLE"):
            await adapter.analyze("https://example.com/video.mp4", 4_000)

    assert attempts == 3
