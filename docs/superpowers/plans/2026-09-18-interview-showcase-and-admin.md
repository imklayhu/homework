# Interview Showcase and Admin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an interview-friendly product narrative, safe new-tab navigation, and an upgraded admin presentation without interrupting the video analysis workflow.

**Architecture:** The home route stays as the upload entry point. A static `/product` route contains the product narrative. The authenticated admin routes reuse the protected metrics API and reshape only presentation. Explicit `NEXT_PUBLIC_DEMO_ADMIN_*` variables provide the demo credential tip and remain separate from every model secret.

**Tech Stack:** Next.js 16, React 19, TypeScript, Vitest, CSS, existing FastAPI metrics API.

---

### Task 1: Navigation and product narrative

**Files:**

- Create: `apps/web/src/app/product/page.tsx`
- Modify: `apps/web/src/app/page.tsx`
- Modify: `apps/web/src/app/globals.css`
- Create: `apps/web/tests/product-page.test.tsx`

- [ ] Write a failing Vitest test that renders `Home`, finds the `产品方案` and `数据看板` links, and asserts `target="_blank"` on both links.
- [ ] Write a failing Vitest test that renders the new `ProductPage`, finds heading `把教育长视频变成可验证、可复用的内容资产`, and finds heading `三阶段产品路线`.
- [ ] Run `cd apps/web && npm test -- product-page.test.tsx`; expect failure because the product route and navigation do not yet exist.
- [ ] Add `<nav className="site-nav" aria-label="主导航">` to `page.tsx`; it contains `开始体验` as an in-tab home link plus `产品方案` and `数据看板` as links with `target="_blank" rel="noreferrer"`.
- [ ] Create `product/page.tsx` with semantic sections for product positioning, product loop, delivered MVP, product decisions, measurement system, and the reliability/content-quality/workflow roadmap.
- [ ] Add responsive navigation, product hero, card, metric, and roadmap CSS using existing global variables.
- [ ] Run `cd apps/web && npm test -- product-page.test.tsx`; expect pass.
- [ ] Commit navigation, route, CSS, and test with message `feat: add interview product showcase`.

### Task 2: Admin login and dashboard presentation

**Files:**

- Modify: `apps/web/src/app/admin/login/page.tsx`
- Modify: `apps/web/src/app/admin/dashboard/page.tsx`
- Modify: `apps/web/src/app/globals.css`
- Create: `apps/web/tests/admin-showcase.test.tsx`

- [ ] Write a failing test that renders `AdminLogin` and requires visible `演示账号` and `演示密码` text below the form.
- [ ] Write a failing test that mocks a successful `GET /api/admin/metrics`, renders `Dashboard`, and requires `经营总览`, `任务漏斗`, and `失败归因` headings.
- [ ] Run `cd apps/web && npm test -- admin-showcase.test.tsx`; expect failure because the new hint and dashboard sections do not exist.
- [ ] Add the `demo-credentials` aside after the form, showing `NEXT_PUBLIC_DEMO_ADMIN_USERNAME` and `NEXT_PUBLIC_DEMO_ADMIN_PASSWORD` with safe display fallbacks.
- [ ] Restructure the dashboard into KPI cards, a task funnel, performance and cost cards, Remix conversion, event adoption, daily trend rows, and a failure-reason/recent-failure card. Preserve the existing 401 redirect and logout request.
- [ ] Add responsive CSS for the login panel, admin KPI grid, section cards, funnel rows, trends, and failure list.
- [ ] Run `cd apps/web && npm test -- admin-showcase.test.tsx`; expect pass.
- [ ] Commit login, dashboard, CSS, and test with message `feat: improve interview admin dashboard`.

### Task 3: Demo configuration, verification, and deployment

**Files:**

- Modify: `.env.example`
- Modify: `README.md`

- [ ] Document `NEXT_PUBLIC_DEMO_ADMIN_USERNAME=admin` and `NEXT_PUBLIC_DEMO_ADMIN_PASSWORD=` as demo-only values. State that they must match the low-privilege admin login but no model key, base URL, or session secret may ever have a `NEXT_PUBLIC_` prefix.
- [ ] Run `cd apps/web && npm test && npm run lint && npm run build`; expect all commands to exit zero.
- [ ] Rebuild and deploy Lighthouse and Ubuntu using each server’s existing `.env` file. Add the two public demo variables without printing any secret values.
- [ ] Smoke test `/`, `/product`, and `/admin/login` over the Lighthouse public domain. Verify unauthenticated `/api/admin/metrics` returns HTTP 401.
- [ ] Commit `.env.example` and `README.md` with message `docs: document interview demo configuration`.
