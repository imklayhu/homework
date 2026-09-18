import { afterEach, describe, expect, it, vi } from "vitest";

describe("API URL construction", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sends an upload to the single /api prefix in same-origin deployments", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ video_id: "video-1", job_id: "job-1", status: "queued" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const { buildApiUrl, uploadVideo } = await import("../src/lib/api");
    expect(buildApiUrl("/api/videos", "/api")).toBe("/api/videos");

    await uploadVideo(new File(["video"], "lesson.mp4", { type: "video/mp4" }));

    expect(fetchMock.mock.calls[0][0]).not.toContain("/api/api/");
  });
});
