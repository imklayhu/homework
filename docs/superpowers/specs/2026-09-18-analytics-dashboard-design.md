# Analytics Dashboard Design

## Goal

Make the admin dashboard useful for product and reliability decisions while preserving the current SQLite deployment and existing admin authentication. Historical business records are included, and new behavioral/stage events are recorded going forward.

## Metrics

- Usage: videos, total duration, upload bytes, active sessions.
- Jobs: total, completed, failed, in-progress, retry rate, completion rate.
- Performance: upload/analysis duration and stage duration (average plus P50/P95 where enough samples exist).
- Quality: failure stages, error codes, and recent failed jobs.
- Model: calls, token usage, estimated cost, and average cost per completed analysis.
- Remix: created/completed/failed jobs, completion rate, output duration, and selected segment count.
- Trends: daily videos, jobs, success/failure, and estimated cost for the selected window.

## Data design

Existing `Video`, `AnalysisJob`, `AnalysisResult`, and `RemixJob` rows are the source of truth for historical aggregates. `AnalyticsEvent` remains the append-only event stream for page/session behavior and lifecycle details. Event properties are JSON and must not contain API keys, video contents, or passwords. Event names use stable snake_case names such as `video_upload_started`, `video_upload_completed`, `analysis_stage_changed`, `analysis_completed`, `analysis_failed`, `analysis_retried`, `remix_created`, `remix_completed`, and `remix_failed`.

The API will expose one authenticated metrics response with a 30-day default window and an optional bounded `days` parameter. It will include KPI cards, daily trend rows, funnel counts, duration summaries, error/model/remix breakdowns, and recent failures. Empty datasets return zeroes and empty arrays rather than errors.

## UI

The existing `/admin/dashboard` route remains protected by the current admin session. It will show summary cards, a daily trend table, lifecycle funnel, performance breakdown, failure ranking/recent failures, model cost usage, and Remix usage. No public dashboard route is added.

## Compatibility and safety

No new external analytics service or database is introduced. Existing `/api/admin/metrics` remains the endpoint and keeps `total_events`/`events` for compatibility while adding structured fields. The change is local-only until explicitly deployed later.

## Validation

Tests cover historical aggregation, event/lifecycle aggregation, empty data, bounded date windows, admin authorization, and dashboard rendering of the structured response. API and web regression suites must remain green.
