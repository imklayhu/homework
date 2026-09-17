import { render, screen } from "@testing-library/react";

import { JobProgress } from "@/components/JobProgress";


test("shows the current real processing stage", () => {
  render(<JobProgress status="understanding" />);
  expect(screen.getByText("理解视频内容")).toHaveAttribute("aria-current", "step");
});


test("shows actionable failure message", () => {
  render(<JobProgress status="failed" errorMessage="视频分析超时，请重试。" onRetry={() => undefined} />);
  expect(screen.getByText("视频分析超时，请重试。")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "重新分析" })).toBeInTheDocument();
});
