# Simplified Chunked Video Upload Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the browser's single large upload request with sequential 8 MiB chunks that work through Cloudflare Tunnel and feed the existing analysis pipeline.

**Architecture:** A filesystem-backed upload service owns manifests, atomic chunk writes, ordered assembly, and expiry cleanup under `data/tmp/chunk-uploads`. A dedicated FastAPI router exposes init/chunk/complete endpoints and delegates the completed file to the same video-registration logic used by the legacy endpoint. The Web client uploads chunks sequentially with bounded retry and reports confirmed progress to `UploadPanel`.

**Tech Stack:** FastAPI, Pydantic, SQLModel, pathlib, Next.js 16, React 19, TypeScript, Vitest, pytest.

---

## File Structure

- Create `apps/api/app/services/chunk_uploads.py`: manifest persistence, chunk validation/write, assembly, expiry cleanup.
- Create `apps/api/app/routes/uploads.py`: init, chunk and complete HTTP contract.
- Create `apps/api/tests/test_chunk_upload_api.py`: endpoint and filesystem integration tests.
- Modify `apps/api/app/schemas.py`: chunk-upload request/response models.
- Modify `apps/api/app/routes/videos.py`: extract reusable completed-file registration function.
- Modify `apps/api/app/main.py`: register uploads router.
- Modify `apps/api/app/config.py`: chunk size and upload-expiry settings.
- Modify `apps/web/src/lib/api.ts`: sequential chunk client, retry, progress callback.
- Modify `apps/web/src/components/UploadPanel.tsx`: receive and display confirmed progress.
- Modify `apps/web/src/app/page.tsx`: connect progress callback and navigate after completion.
- Create `apps/web/tests/chunk-upload.test.ts`: slicing, request order and retry tests.
- Modify `apps/web/tests/UploadPanel.test.tsx`: progress UI coverage.

### Task 1: Filesystem-backed chunk sessions

**Files:**
- Create: `apps/api/app/services/chunk_uploads.py`
- Modify: `apps/api/app/config.py`
- Test: `apps/api/tests/test_chunk_uploads.py`

- [ ] **Step 1: Write failing service tests**

Cover manifest creation, exact expected sizes for normal/last chunks, atomic overwrite, missing-chunk detection, ordered assembly, actual-size verification, and cleanup of sessions older than 24 hours. Use a 10-byte declared file with 4-byte chunks so tests stay fast.

- [ ] **Step 2: Verify RED**

Run: `cd apps/api && uv run pytest tests/test_chunk_uploads.py -v`

Expected: collection fails because `app.services.chunk_uploads` does not exist.

- [ ] **Step 3: Implement the service**

Define immutable Pydantic `UploadManifest`, `create_session()`, `load_manifest()`, `write_chunk()`, `assemble_chunks()`, `remove_session()`, and `cleanup_expired_sessions()`. Generate UUID paths server-side, use `Path.replace()` for atomic manifest/chunk writes, stream assembly in 1 MiB blocks, and raise `AppError` with `UPLOAD_NOT_FOUND`, `INVALID_CHUNK`, `MISSING_CHUNKS`, or `FILE_SIZE_MISMATCH`.

Add settings:

```python
chunk_upload_size: int = 8 * 1024 * 1024
chunk_upload_ttl_seconds: int = 24 * 60 * 60

@property
def chunk_uploads_dir(self) -> Path:
    return self.temp_dir / "chunk-uploads"
```

- [ ] **Step 4: Verify GREEN**

Run: `cd apps/api && uv run pytest tests/test_chunk_uploads.py -v`

Expected: all service tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/config.py apps/api/app/services/chunk_uploads.py apps/api/tests/test_chunk_uploads.py
git commit -m "feat: add filesystem chunk upload sessions"
```

### Task 2: Chunk upload API and existing pipeline integration

**Files:**
- Create: `apps/api/app/routes/uploads.py`
- Create: `apps/api/tests/test_chunk_upload_api.py`
- Modify: `apps/api/app/routes/videos.py`
- Modify: `apps/api/app/schemas.py`
- Modify: `apps/api/app/main.py`

- [ ] **Step 1: Write failing endpoint tests**

Test init success, invalid MIME, oversized declaration, inconsistent chunk count, a complete multi-chunk upload, out-of-range/incorrect-size chunks, missing chunks on complete, duplicate overwrite, and cleanup after successful registration. Patch `probe_video` to return deterministic duration/dimensions while asserting assembled bytes match the fixture.

- [ ] **Step 2: Verify RED**

Run: `cd apps/api && uv run pytest tests/test_chunk_upload_api.py -v`

Expected: init route returns 404.

- [ ] **Step 3: Add schemas and reusable registration**

Add `ChunkUploadInit`, `ChunkUploadCreated`, and constraints to `schemas.py`. Extract `register_uploaded_video(path, original_name, mime_type, size_bytes, background_tasks, session, settings)` from `upload_video`; it probes, validates, atomically moves the source, commits `Video`/`AnalysisJob`, schedules analysis, and removes partial final output on failure.

- [ ] **Step 4: Implement and register routes**

Implement:

```text
POST /api/uploads/init                 -> 201 ChunkUploadCreated
PUT  /api/uploads/{id}/chunks/{index} -> 204
POST /api/uploads/{id}/complete       -> 202 UploadAccepted
```

The complete endpoint assembles to `{session}/assembled.upload`, calls `register_uploaded_video`, and removes the session only after success. Register the router in `main.py`.

- [ ] **Step 5: Verify endpoint and regression tests**

Run: `cd apps/api && uv run pytest -q`

Expected: all API tests pass, including legacy `POST /api/videos`.

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/routes/uploads.py apps/api/app/routes/videos.py apps/api/app/schemas.py apps/api/app/main.py apps/api/tests/test_chunk_upload_api.py
git commit -m "feat: expose chunked video upload api"
```

### Task 3: Sequential Web chunk client with retry

**Files:**
- Modify: `apps/web/src/lib/api.ts`
- Create: `apps/web/tests/chunk-upload.test.ts`

- [ ] **Step 1: Write failing client tests**

With a 10-byte `File` and injected chunk size 4, assert calls occur as init, chunks 0/1/2 in order, then complete; assert raw sliced bodies are 4/4/2 bytes; assert confirmed progress is 40/80/100; assert a transient chunk failure retries and a third failure rejects without calling complete.

- [ ] **Step 2: Verify RED**

Run: `cd apps/web && npm test -- --run tests/chunk-upload.test.ts`

Expected: failure because `uploadVideoInChunks` is missing.

- [ ] **Step 3: Implement minimal client**

Add `CHUNK_SIZE = 8 * 1024 * 1024`, `sleep`, and:

```typescript
uploadVideoInChunks(
  file: File,
  onProgress?: (progress: { percent: number; uploadedChunks: number; totalChunks: number }) => void,
  options?: { chunkSize?: number; retryDelaysMs?: number[] },
): Promise<{ video_id: string; job_id: string; status: string }>
```

Use raw Blob bodies and `Content-Type: application/octet-stream`; retry only network errors and `5xx`, but surface `4xx` immediately through `ApiError`. Make `uploadVideo` delegate to the chunk implementation so existing callers automatically switch.

- [ ] **Step 4: Verify GREEN and regression suite**

Run: `cd apps/web && npm test -- --run`

Expected: all Web unit tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/lib/api.ts apps/web/tests/chunk-upload.test.ts apps/web/tests/api.test.ts
git commit -m "feat: upload videos in sequential chunks"
```

### Task 4: Upload progress UI

**Files:**
- Modify: `apps/web/src/components/UploadPanel.tsx`
- Modify: `apps/web/src/app/page.tsx`
- Modify: `apps/web/tests/UploadPanel.test.tsx`

- [ ] **Step 1: Write failing UI tests**

Change the `onUpload` test double to receive a progress callback, emit `{percent: 48, uploadedChunks: 6, totalChunks: 13}`, and assert visible text `正在上传 48%（6/13）`. Preserve unsupported-format and error tests.

- [ ] **Step 2: Verify RED**

Run: `cd apps/web && npm test -- --run tests/UploadPanel.test.tsx`

Expected: progress text is absent.

- [ ] **Step 3: Implement progress wiring**

Change the prop to `(file, onProgress) => Promise<void>`, keep progress state local to `UploadPanel`, reset it for each selection, show confirmed percent/chunk counts while uploading, and pass the callback from `page.tsx` into `uploadVideo`.

- [ ] **Step 4: Verify GREEN and production build**

Run: `cd apps/web && npm test -- --run && npm run build`

Expected: tests pass and Next production build completes.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/components/UploadPanel.tsx apps/web/src/app/page.tsx apps/web/tests/UploadPanel.test.tsx
git commit -m "feat: show chunk upload progress"
```

### Task 5: Full verification and Ubuntu deployment

**Files:**
- Modify only if verification reveals a scoped defect.

- [ ] **Step 1: Run local verification**

```bash
cd apps/api && uv run pytest -q
cd ../web && npm test -- --run && npm run build
git diff --check
```

Expected: all tests/builds pass and diff check is clean.

- [ ] **Step 2: Sync code and current `.env`**

Use rsync excluding `.env`, `data`, `.git`, build outputs and caches; then copy the current local `.env` explicitly with `scp` and set remote mode `600`.

- [ ] **Step 3: Rebuild and converge Compose**

Run remotely:

```bash
cd /home/klay/docker/stacks/framewise
docker compose up -d --build --remove-orphans
docker compose ps
```

Expected: exactly `framewise-api-1` healthy and `framewise-web-1` bound to `0.0.0.0:3015->3000`.

- [ ] **Step 4: Test an upload through port 3015**

Upload a valid file larger than 10 MiB through init/chunk/complete and assert final response `202`, then inspect API/Web logs for absence of 500.

- [ ] **Step 5: Cloudflare acceptance**

Have the user upload the original video through the configured Tunnel URL. Confirm each request remains near 8 MiB and the browser reaches the job page.
