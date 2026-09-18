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

export type UploadProgress = { percent: number; uploadedChunks: number; totalChunks: number };
type UploadResult = { video_id: string; job_id: string; status: string };
const CHUNK_SIZE = 8 * 1024 * 1024;

const delay = (milliseconds: number) => new Promise((resolve) => setTimeout(resolve, milliseconds));

async function putChunk(path: string, body: Blob, retryDelaysMs: number[]): Promise<void> {
  for (let attempt = 0; ; attempt += 1) {
    try {
      const response = await fetch(buildApiUrl(path), { method: "PUT", headers: { "content-type": "application/octet-stream" }, body });
      if (response.ok) return;
      if (response.status < 500 || attempt >= retryDelaysMs.length) {
        const payload = await response.json().catch(() => ({ code: "UPLOAD_FAILED", message: "分片上传失败，请重试。" }));
        throw new ApiError(payload.code, payload.message, response.status);
      }
    } catch (error) {
      if (error instanceof ApiError || attempt >= retryDelaysMs.length) throw error;
    }
    await delay(retryDelaysMs[attempt]);
  }
}

export async function uploadVideo(
  file: File,
  onProgress?: (progress: UploadProgress) => void,
  options?: { chunkSize?: number; retryDelaysMs?: number[] },
): Promise<UploadResult> {
  const chunkSize = options?.chunkSize ?? CHUNK_SIZE;
  const retryDelaysMs = options?.retryDelaysMs ?? [500, 1000];
  const totalChunks = Math.ceil(file.size / chunkSize);
  const created = await request<{ upload_id: string }>("/api/uploads/init", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ filename: file.name, content_type: file.type, size_bytes: file.size, chunk_size: chunkSize, total_chunks: totalChunks }),
  });
  for (let index = 0; index < totalChunks; index += 1) {
    await putChunk(`/api/uploads/${created.upload_id}/chunks/${index}`, file.slice(index * chunkSize, Math.min(file.size, (index + 1) * chunkSize)), retryDelaysMs);
    onProgress?.({ percent: Math.round(((index + 1) / totalChunks) * 100), uploadedChunks: index + 1, totalChunks });
  }
  return request<UploadResult>(`/api/uploads/${created.upload_id}/complete`, { method: "POST" });
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
