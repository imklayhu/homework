import { expect, test } from "@playwright/test";
import demoResult from "../../../../samples/demo-result.json";

const job = {
  id: "job-demo",
  video_id: "video-demo",
  status: "completed",
  current_stage: "completed",
  error_code: null,
  error_message: null,
  provider_usage: { prompt_tokens: 1200, completion_tokens: 300 },
  estimated_cost: 0.02,
  created_at: "2026-09-17T00:00:00Z",
  updated_at: "2026-09-17T00:01:00Z",
};

test("upload, inspect evidence, order insights, and download a Remix", async ({ page }) => {
  const remixRequests: string[][] = [];
  await page.route("http://localhost:8000/api/**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === "/api/videos" && route.request().method() === "POST") {
      await route.fulfill({ status: 202, json: { video_id: "video-demo", job_id: "job-demo", status: "uploaded" } });
    } else if (url.pathname === "/api/jobs/job-demo") {
      await route.fulfill({ json: job });
    } else if (url.pathname === "/api/jobs/job-demo/result") {
      await route.fulfill({ json: demoResult });
    } else if (url.pathname === "/api/videos/video-demo/remixes") {
      remixRequests.push((await route.request().postDataJSON()).insight_ids);
      await route.fulfill({ status: 202, json: { id: "remix-demo", video_id: "video-demo", status: "completed", duration_ms: 1900, download_url: "/api/remixes/remix-demo/download", error_code: null } });
    } else if (url.pathname === "/api/videos/video-demo/content" || url.pathname === "/api/remixes/remix-demo/download") {
      await route.fulfill({ status: 200, contentType: "video/mp4", body: Buffer.from([]) });
    } else {
      await route.abort();
    }
  });

  await page.goto("/");
  await page.getByLabel("选择视频").setInputFiles("../api/tests/fixtures/sample.mp4");
  await expect(page).toHaveURL(/\/jobs\/job-demo$/);
  await expect(page.getByRole("heading", { name: demoResult.summary })).toBeVisible();
  await expect(page.getByText("每个判断都要能够回到原始证据。")).toBeVisible();

  await page.getByRole("button", { name: /加入 Remix/ }).nth(0).click();
  await page.getByRole("button", { name: /加入 Remix/ }).nth(0).click();
  await page.getByRole("button", { name: "上移证据需要回到原始内容" }).click();
  await page.getByRole("button", { name: "生成 Remix" }).click();

  await expect(page.getByRole("heading", { name: "你的观点短片已生成" })).toBeVisible();
  await expect(page.getByRole("link", { name: /下载 MP4/ })).toHaveAttribute("href", /remix-demo\/download$/);
  expect(remixRequests).toEqual([["insight-2", "insight-1"]]);
});

test("refreshing a completed job restores the workspace", async ({ page }) => {
  await page.route("http://localhost:8000/api/jobs/job-demo", (route) => route.fulfill({ json: job }));
  await page.route("http://localhost:8000/api/jobs/job-demo/result", (route) => route.fulfill({ json: demoResult }));
  await page.route("http://localhost:8000/api/videos/video-demo/content", (route) => route.fulfill({ contentType: "video/mp4", body: Buffer.from([]) }));
  await page.goto("/jobs/job-demo");
  await expect(page.getByRole("heading", { name: "教学观点", exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByText("先定义可验证的问题")).toBeVisible();
});
