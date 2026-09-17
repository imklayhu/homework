import { expect, test } from "@playwright/test";

test("rejects an unsupported upload before making an API request", async ({ page }) => {
  let requests = 0;
  await page.route("http://localhost:8000/api/videos", async (route) => { requests += 1; await route.abort(); });
  await page.goto("/");
  await page.getByLabel("选择视频").setInputFiles({ name: "notes.txt", mimeType: "text/plain", buffer: Buffer.from("not video") });
  await expect(page.getByText("仅支持 MP4、MOV 和 WebM 视频。")).toBeVisible();
  expect(requests).toBe(0);
});

test("shows a recoverable model authorization failure without leaking internals", async ({ page }) => {
  await page.route("http://localhost:8000/api/jobs/job-failed", (route) => route.fulfill({ json: {
    id: "job-failed",
    video_id: "video-demo",
    status: "failed",
    current_stage: "failed",
    error_code: "MODEL_AUTH_FAILED",
    error_message: "模型服务暂时不可用，请检查配置后重新分析。",
    provider_usage: null,
    estimated_cost: null,
    created_at: "2026-09-17T00:00:00Z",
    updated_at: "2026-09-17T00:01:00Z",
  } }));
  await page.goto("/jobs/job-failed");
  await expect(page.getByText("模型服务暂时不可用，请检查配置后重新分析。")).toBeVisible();
  await expect(page.getByRole("button", { name: "重新分析" })).toBeVisible();
  await expect(page.locator("body")).not.toContainText(/API[_ -]?KEY|https?:\/\/.*dashscope|Traceback|\/Users\//i);
});
