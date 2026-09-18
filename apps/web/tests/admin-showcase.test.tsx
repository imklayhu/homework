import { render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn(), replace: vi.fn() }) }));

import AdminLogin from "@/app/admin/login/page";
import Dashboard from "@/app/admin/dashboard/page";

test("shows demo credential hints below the admin login form", () => {
  render(<AdminLogin />);

  expect(screen.getByText(/演示账号/i)).toBeInTheDocument();
  expect(screen.getByText(/演示密码/i)).toBeInTheDocument();
});

test("presents the dashboard as an operational overview", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      window_days: 30,
      total_events: 4,
      events: { video_upload_completed: 2 },
      usage: { videos: 2, duration_ms: 240000, bytes: 1000 },
      jobs: { total: 2, completed: 1, failed: 1, in_progress: 0, completion_rate: 50, retry_count: 1 },
      performance: { analysis_seconds: { avg: 25, p50: 20, p95: 40 } },
      failures: { by_code: { MODEL_TIMEOUT: 1 }, recent: [{ id: "f1", stage: "understanding", code: "MODEL_TIMEOUT" }] },
      model: { calls: 2, total_tokens: 100, estimated_cost: 0.2, average_cost: 0.1 },
      remix: { total: 1, completed: 1, failed: 0, completion_rate: 100, duration_ms: 30000 },
      daily: [{ date: "2026-09-18", jobs: 2, videos: 2, completed: 1, failed: 1, cost: 0.2 }],
    }),
  }));

  render(<Dashboard />);
  expect(await screen.findByRole("heading", { name: "经营总览" })).toBeInTheDocument();
  expect(screen.getByText("任务漏斗")).toBeInTheDocument();
  expect(screen.getByText("失败归因")).toBeInTheDocument();
  await waitFor(() => vi.unstubAllGlobals());
});
