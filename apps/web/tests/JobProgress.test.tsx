import { render, screen } from "@testing-library/react";

import { JobProgress } from "@/components/JobProgress";
import type { AnalysisJob } from "@/lib/types";


function job(overrides: Partial<AnalysisJob> = {}): AnalysisJob {
  return {
    id: "job",
    video_id: "video",
    status: "understanding",
    current_stage: "understanding",
    error_code: null,
    error_message: null,
    provider_usage: null,
    estimated_cost: null,
    progress_current: 2,
    progress_total: 15,
    progress_percent: 13,
    progress_message: "正在理解第 3/15 个片段（01:00–01:30）",
    logs: [{ id: "log-1", stage: "understanding", level: "info", message: "正在理解第 3/15 个片段（01:00–01:30）", created_at: "2026-09-18T10:00:00Z" }],
    created_at: "2026-09-18T10:00:00Z",
    updated_at: "2026-09-18T10:00:01Z",
    ...overrides,
  };
}


test("shows the current real processing stage", () => {
  render(<JobProgress job={job()} />);
  expect(screen.getByText("理解视频内容")).toHaveAttribute("aria-current", "step");
  expect(screen.getByText("第 3/15 个片段")).toBeInTheDocument();
  expect(screen.getByText("13%")).toBeInTheDocument();
  expect(screen.getByRole("list", { name: "分析日志" })).toBeInTheDocument();
});


test("shows actionable failure message", () => {
  render(<JobProgress job={job({ status: "failed", current_stage: "failed", error_message: "视频分析超时，请重试。", logs: [] })} onRetry={() => undefined} />);
  expect(screen.getByText("视频分析超时，请重试。")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "重新分析" })).toBeInTheDocument();
});


test("shows preparation message when no progress logs exist", () => {
  render(<JobProgress job={job({ logs: [], progress_message: null })} />);
  expect(screen.getByText("正在准备视频理解")).toBeInTheDocument();
});
