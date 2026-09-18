import { afterEach, describe, expect, it, vi } from "vitest";

import { uploadVideo } from "../src/lib/api";

describe("chunked video upload", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("uses 1 MiB chunks by default so slow tunnel uploads finish within the proxy window", async () => {
    const initBodies: unknown[] = [];
    vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/init")) {
        initBodies.push(JSON.parse(String(init?.body)));
        return { ok: true, json: async () => ({ upload_id: "upload-1" }) } as Response;
      }
      if (url.endsWith("/complete")) {
        return { ok: true, json: async () => ({ video_id: "v", job_id: "j", status: "uploaded" }) } as Response;
      }
      return { ok: true, status: 204 } as Response;
    }));

    await uploadVideo(new File([new Uint8Array(1024 * 1024 + 1)], "lesson.mp4", { type: "video/mp4" }));

    expect(initBodies).toEqual([expect.objectContaining({ chunk_size: 1024 * 1024, total_chunks: 2 })]);
  });

  it("uploads chunks in order and reports confirmed progress", async () => {
    const calls: string[] = [];
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      calls.push(`${init?.method}:${url}`);
      if (url.endsWith("/init")) return { ok: true, json: async () => ({ upload_id: "upload-1" }) } as Response;
      if (url.endsWith("/complete")) return { ok: true, json: async () => ({ video_id: "v", job_id: "j", status: "uploaded" }) } as Response;
      return { ok: true, status: 204 } as Response;
    });
    vi.stubGlobal("fetch", fetchMock);
    const progress = vi.fn();
    await uploadVideo(new File(["abcdefghij"], "lesson.mp4", { type: "video/mp4" }), progress, { chunkSize: 4, retryDelaysMs: [] });
    expect(calls).toEqual(["POST:http://localhost:8000/api/uploads/init", "PUT:http://localhost:8000/api/uploads/upload-1/chunks/0", "PUT:http://localhost:8000/api/uploads/upload-1/chunks/1", "PUT:http://localhost:8000/api/uploads/upload-1/chunks/2", "POST:http://localhost:8000/api/uploads/upload-1/complete"]);
    expect(progress.mock.calls.map(([value]) => value.percent)).toEqual([33, 67, 100]);
  });

  it("retries a transient chunk failure", async () => {
    let chunkAttempts = 0;
    vi.stubGlobal("fetch", vi.fn(async (url: string) => {
      if (url.endsWith("/init")) return { ok: true, json: async () => ({ upload_id: "upload-1" }) } as Response;
      if (url.includes("/chunks/")) { chunkAttempts += 1; if (chunkAttempts === 1) throw new TypeError("network"); return { ok: true, status: 204 } as Response; }
      return { ok: true, json: async () => ({ video_id: "v", job_id: "j", status: "uploaded" }) } as Response;
    }));
    await uploadVideo(new File(["abcd"], "lesson.mp4", { type: "video/mp4" }), undefined, { chunkSize: 4, retryDelaysMs: [0, 0] });
    expect(chunkAttempts).toBe(2);
  });
});
