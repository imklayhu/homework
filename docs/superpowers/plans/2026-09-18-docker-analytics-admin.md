# Docker Analytics Admin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended). Steps use checkbox (`- [ ]`) syntax.

**Goal:** Deploy Framewise on the Ubuntu home server with LAN/Tailscale access and an authenticated analytics dashboard.

**Architecture:** Add an API-owned SQLite event store and cookie-based admin session, Next.js admin routes consuming protected aggregate endpoints, and production Docker images for Web/API with a Compose bind-mounted data directory.

**Tech Stack:** FastAPI, SQLModel/SQLite, PBKDF2, Next.js, Docker Compose, FFmpeg.

---

### Task 1: Event store and admin authentication

- Add SQLModel event/session tables, migration-safe initialization, password hashing and signed HttpOnly session cookie.
- Add protected aggregate endpoints and tests for login, unauthorized access, and metric aggregation.

### Task 2: Instrument product flows

- Emit server events for upload, analysis state transitions, model usage/cost, remix completion/failure and download.
- Add frontend event calls for insight selection/order and dashboard interaction where server context is unavailable.

### Task 3: Admin dashboard UI

- Add `/admin/login` and `/admin/dashboard`, login form, KPI cards, failure table, cost/time summary and logout.
- Add component and E2E coverage with mocked API responses.

### Task 4: Docker deployment

- Add API/Web Dockerfiles, Compose file, production environment example and Ubuntu deployment README/script.
- Use port 3015, persistent `/app/data`, health checks, restart policy, no public router exposure.

### Task 5: Verification and handoff

- Run tests/build/E2E, `docker compose config`, credential scan and deploy-safe config checks.
- Generate a random admin credential only in local ignored `.env` and document rotation.
