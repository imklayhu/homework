# Short Tail Video Segment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent model failures caused by sub-three-second trailing video segments while preserving all source content.

**Architecture:** Build concrete segment ranges before preprocessing, merging an undersized final range into its predecessor. Use those same ranges for progress totals, ffmpeg arguments, model duration, and output timestamp offsets so all consumers share one source of truth.

**Tech Stack:** Python 3.12, pytest, asyncio, SQLModel, Docker Compose

---

### Task 1: Add the regression test

**Files:**
- Modify: `apps/api/tests/test_analysis.py`

- [ ] **Step 1: Write the failing test**

Add this async regression test, reusing the existing fixture model result setup from `test_long_video_uses_model_friendly_segment_duration`:

```python
@pytest.mark.asyncio
async def test_tiny_tail_is_merged_into_previous_segment(tmp_path: Path, monkeypatch) -> None:
    raw = json.loads(MODEL_RESPONSE.read_text())
    result = ModelAnalysisResult(
        AnalysisPayload.model_validate(json.loads(raw["choices"][0]["message"]["content"])),
        raw["usage"],
        "qwen3-vl-flash",
        "qwen-video-v1",
    )
    adapter = TrackingAdapter(result=result)
    ranges: list[tuple[float, float]] = []

    def fake_proxy(source, destination, start_seconds=0, duration_seconds=None):
        ranges.append((start_seconds, duration_seconds))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"proxy")
        return destination

    monkeypatch.setattr("app.services.analysis.create_analysis_proxy", fake_proxy)
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")

    await analyze_in_segments(source, 420_350, tmp_path, "job", adapter)

    assert len(ranges) == 14
    assert ranges[-1] == (390.0, 30.35)
    assert adapter.calls == 14
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
cd apps/api && uv run pytest tests/test_analysis.py::test_tiny_tail_is_merged_into_previous_segment -q
```

Expected: failure showing 15 model calls or a final 0.35-second proxy.

### Task 2: Implement shared segment ranges

**Files:**
- Modify: `apps/api/app/services/analysis.py`
- Modify: `apps/api/app/services/job_progress.py`
- Modify: `apps/api/tests/test_analysis.py`

- [ ] **Step 1: Add `build_segment_ranges`**

Create a pure helper equivalent to:

```python
def build_segment_ranges(
    duration_ms: int,
    segment_ms: int = 30_000,
    min_tail_ms: int = 3_000,
) -> list[tuple[int, int]]:
    ranges = [
        (start_ms, min(segment_ms, duration_ms - start_ms))
        for start_ms in range(0, duration_ms, segment_ms)
    ]
    if len(ranges) > 1 and ranges[-1][1] < min_tail_ms:
        previous_start, previous_length = ranges[-2]
        ranges[-2] = (previous_start, previous_length + ranges[-1][1])
        ranges.pop()
    return ranges
```

- [ ] **Step 2: Use actual ranges throughout analysis**

Change `initialize_progress` to accept `total_segments: int`, use `max(1, total_segments)`, and update its direct test call from `(65_000, 30_000)` to `3`. In `analyze_in_segments`, build `segment_ranges`, initialize progress with `len(segment_ranges)`, iterate over `(start_ms, length_ms)`, and offset merged results with `segment_ranges[index][0]`.

- [ ] **Step 3: Run the focused test and verify GREEN**

Run:

```bash
cd apps/api && uv run pytest tests/test_analysis.py::test_tiny_tail_is_merged_into_previous_segment -q
```

Expected: one passing test.

- [ ] **Step 4: Run the API test suite**

Run:

```bash
cd apps/api && uv run pytest -q
```

Expected: all tests pass.

### Task 3: Commit and deploy both servers

**Files:**
- Modify: remote `/home/deploy/framewise`
- Modify: remote `/home/klay/docker/stacks/framewise`

- [ ] **Step 1: Commit the implementation**

Commit the regression test and minimal implementation on the current branch.

- [ ] **Step 2: Sync source without overwriting remote `.env` or `data`**

Use the existing deployment paths and exclude `.env`, `.git`, `data`, caches, and build artifacts.

- [ ] **Step 3: Rebuild and restart both Compose services**

Run `docker compose up -d --build` in each remote deployment directory without changing port 3015.

- [ ] **Step 4: Verify deployment**

Confirm `framewise-api-1` and `framewise-web-1` are running, `/api/health` returns HTTP 200, and the container's `analysis.py` hash matches the local file.
