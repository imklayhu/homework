import asyncio
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import ValidationError

from app.errors import AppError
from app.schemas import AnalysisPayload
from app.services.prompts import ANALYSIS_PROMPT_VERSION, SYSTEM_PROMPT, build_analysis_prompt


@dataclass(frozen=True)
class ModelAnalysisResult:
    payload: AnalysisPayload
    usage: dict[str, Any]
    model: str
    prompt_version: str


class BailianVideoAdapter:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str = "qwen3-vl-flash",
        client: httpx.AsyncClient | None = None,
        sleep: Callable[[float], Any] = asyncio.sleep,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.client = client
        self.sleep = sleep

    async def analyze(self, video_url: str, duration_ms: int) -> ModelAnalysisResult:
        request = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "video_url", "video_url": {"url": video_url, "fps": 0.5}},
                        {"type": "text", "text": build_analysis_prompt(duration_ms)},
                    ],
                },
            ],
            "temperature": 0.1,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "video_analysis",
                    "strict": True,
                    "schema": AnalysisPayload.model_json_schema(),
                },
            },
        }
        data = await self._post_with_retry(request)
        try:
            content = data["choices"][0]["message"]["content"]
            payload = AnalysisPayload.model_validate(json.loads(content))
        except (KeyError, IndexError, TypeError, json.JSONDecodeError, ValidationError) as exc:
            raise AppError("INVALID_MODEL_OUTPUT", "模型返回的分析结果格式无效。", 502) from exc
        return ModelAnalysisResult(
            payload=payload,
            usage=data.get("usage", {}),
            model=data.get("model", self.model),
            prompt_version=ANALYSIS_PROMPT_VERSION,
        )

    async def _post_with_retry(self, body: dict[str, Any]) -> dict[str, Any]:
        owns_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=httpx.Timeout(180, connect=10))
        try:
            for attempt in range(3):
                try:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json=body,
                    )
                except httpx.TimeoutException as exc:
                    if attempt == 2:
                        raise AppError("MODEL_TIMEOUT", "视频分析超时，请重试。", 504) from exc
                    await self._sleep(2**attempt)
                    continue

                if response.status_code in (401, 403):
                    raise AppError("MODEL_AUTH_FAILED", "模型服务认证失败，请检查配置。", 502)
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt == 2:
                        raise AppError("MODEL_UNAVAILABLE", "模型服务暂时不可用，请重试。", 503)
                    await self._sleep(2**attempt)
                    continue
                if response.is_error:
                    raise AppError("MODEL_REQUEST_FAILED", "模型无法处理当前视频。", 502)
                return response.json()
        finally:
            if owns_client:
                await client.aclose()
        raise AppError("MODEL_UNAVAILABLE", "模型服务暂时不可用，请重试。", 503)

    async def _sleep(self, seconds: float) -> None:
        result = self.sleep(seconds)
        if result is not None and hasattr(result, "__await__"):
            await result
