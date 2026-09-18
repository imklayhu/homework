# Long Video Proxy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Make 3–15 minute uploads analyzable by sending a bounded-size proxy video to the model while preserving the original video for evidence and Remix.

**Architecture:** During analysis, probe the original file and create a temporary H.264 proxy at 480p, 0.5 FPS, and bounded bitrate. Send the proxy as a Base64 data URL; retain the original duration/time scale in the prompt and use the original file for all playback and FFmpeg output. Clean proxy files after analysis.

**Tech Stack:** Python, FFmpeg/ffprobe, FastAPI background tasks, pytest.

---

### Task 1: Proxy media helper

**Files:** `apps/api/app/services/media.py`, `apps/api/tests/test_media.py`

- [ ] Add a failing test that invokes the proxy helper on the fixture video and asserts the output exists, is MP4, and has the same duration within 2 seconds.
- [ ] Implement a subprocess-based FFmpeg helper with `scale=-2:480`, `fps=0.5`, H.264/AAC, and a bounded video bitrate; raise `MEDIA_PREPROCESSING_FAILED` on failure.
- [ ] Run the focused media tests and then the full API tests.

### Task 2: Integrate proxy into analysis

**Files:** `apps/api/app/services/analysis.py`, `apps/api/tests/test_analysis.py`

- [ ] Add a failing test proving the adapter receives a proxy data URL rather than the original file for a long video.
- [ ] Create the proxy in `run_analysis`, call the adapter with the proxy and original duration, and remove it in `finally`.
- [ ] Preserve original storage and Remix behavior; map proxy failures to a stable user-facing error.

### Task 3: Real long-video verification

- [ ] Retry Job `2079050a-5d71-40ae-a038-b9620cc9f96a` after the service reloads.
- [ ] Confirm it reaches `completed`, records provider usage, and produces valid insight timestamps.
- [ ] Run `make verify` and inspect `git diff --check`.

