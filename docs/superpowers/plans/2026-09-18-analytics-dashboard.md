# Analytics Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add historical and event-based analytics to the protected admin dashboard without deploying the changes.

**Architecture:** Keep SQLite and `AnalyticsEvent`; add a pure aggregation service that combines business tables with lifecycle events. Extend the existing metrics endpoint compatibly and render structured KPI, trend, funnel, performance, failure, model, and Remix sections in the existing dashboard.

**Tech Stack:** FastAPI, SQLModel, pytest, Next.js, React, Vitest.

---

### Task 1: Define analytics aggregation contract

**Files:**
- Create: `apps/api/app/services/analytics.py`
- Test: `apps/api/tests/test_analytics.py`

- [ ] Write failing tests for empty metrics, historical job counts, duration percentiles, daily trends, error ranking, model cost, and Remix counts.
- [ ] Run `cd apps/api && uv run pytest tests/test_analytics.py -q`; expect failures because the service does not exist.
- [ ] Implement typed aggregation functions using SQLModel queries and JSON parsing; return zero/empty values for missing data and clamp `days` to 1..90.
- [ ] Run the focused tests, then the full API suite.

### Task 2: Expand lifecycle event capture

**Files:**
- Modify: `apps/api/app/services/analysis.py`
- Modify: `apps/api/app/routes/videos.py`
- Modify: `apps/api/app/routes/jobs.py`
- Modify: `apps/api/app/routes/remixes.py`
- Test: `apps/api/tests/test_analytics.py`

- [ ] Add failing tests asserting upload, stage-change, completion/failure, retry, and Remix lifecycle events are persisted with IDs and safe properties.
- [ ] Run the focused tests and verify the new assertions fail.
- [ ] Add one small event helper that serializes only non-secret scalar properties and call it at existing state transitions.
- [ ] Run API regression tests and verify all pass.

### Task 3: Extend the admin metrics endpoint

**Files:**
- Modify: `apps/api/app/routes/admin.py`
- Test: `apps/api/tests/test_admin.py`

- [ ] Write failing endpoint tests for admin authorization, `days` validation, backward-compatible `total_events/events`, and structured sections.
- [ ] Run the endpoint tests and verify failure.
- [ ] Wire the aggregation service into `GET /api/admin/metrics?days=N`, preserving the old keys and returning the new sections.
- [ ] Run all API tests.

### Task 4: Build the richer dashboard view

**Files:**
- Modify: `apps/web/src/app/admin/dashboard/page.tsx`
- Modify: `apps/web/src/app/globals.css`
- Test: `apps/web/tests/admin-dashboard.test.tsx`

- [ ] Add a failing rendering test for KPI cards, funnel, trend, failures, model cost, and Remix sections.
- [ ] Run the Vitest test and verify it fails.
- [ ] Add typed metrics state, loading/error handling, and compact responsive sections to the existing protected route.
- [ ] Run dashboard tests and the complete web test suite.

### Task 5: Verify and document

**Files:**
- Modify: `docs/superpowers/specs/2026-09-18-analytics-dashboard-design.md`

- [ ] Run API and web tests plus production web build.
- [ ] Inspect the diff for secrets and confirm no deployment command or remote mutation was run.
- [ ] Record verification commands and compatibility notes in the design doc.
- [ ] Commit the local implementation only.
