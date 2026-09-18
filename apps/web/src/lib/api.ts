import type { AnalysisJob, AnalysisPayload, RemixJob } from "./types";


const configuredApiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
export const API_BASE_URL = configuredApiBaseUrl.replace(/\/api\/?$/, "");

export const buildApiUrl = (path: string, baseUrl = API_BASE_URL) =>
  `${baseUrl.replace(/\/api\/?$/, "")}${path}`;

export class ApiError extends Error {
  constructor(public code: string, message: string, public status: number) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(buildApiUrl(path), init);
  if (!response.ok) {
    const body = await response.json().catch(() => ({ code: "REQUEST_FAILED", message: "请求失败，请重试。" }));
    throw new ApiError(body.code, body.message, response.status);
  }
  return response.json() as Promise<T>;
}

export async function uploadVideo(file: File): Promise<{ video_id: string; job_id: string; status: string }> {
  const form = new FormData();
  form.append("file", file);
  return request("/api/videos", { method: "POST", body: form });
}

export const getJob = (id: string) => request<AnalysisJob>(`/api/jobs/${id}`);
export const getResult = (id: string) => request<AnalysisPayload>(`/api/jobs/${id}/result`);
export const retryJob = (id: string) => request<AnalysisJob>(`/api/jobs/${id}/retry`, { method: "POST" });
export const createRemix = (videoId: string, insightIds: string[]) => request<RemixJob>(`/api/videos/${videoId}/remixes`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ insight_ids: insightIds }),
});
export const getRemix = (id: string) => request<RemixJob>(`/api/remixes/${id}`);
export const videoUrl = (videoId: string) => `${API_BASE_URL}/api/videos/${videoId}/content`;
export const remixUrl = (remixId: string) => `${API_BASE_URL}/api/remixes/${remixId}/download`;
