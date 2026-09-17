export type JobStatus =
  | "uploaded"
  | "preprocessing"
  | "understanding"
  | "analyzing"
  | "completed"
  | "failed";

export type EvidenceType = "transcript" | "visual";

export interface Video {
  id: string;
  original_name: string;
  duration_ms: number;
  size_bytes: number;
  mime_type: string;
  width: number | null;
  height: number | null;
}

export interface Chapter {
  id: string;
  title: string;
  start_ms: number;
  end_ms: number;
  summary: string;
}

export interface Insight {
  id: string;
  title: string;
  explanation: string;
  start_ms: number;
  end_ms: number;
  transcript_evidence: string;
  visual_evidence: string;
  evidence_types: EvidenceType[];
  confidence: number;
  remix_reason: string;
}

export interface AnalysisPayload {
  summary: string;
  chapters: Chapter[];
  insights: Insight[];
}

export interface AnalysisJob {
  id: string;
  video_id: string;
  status: JobStatus;
  current_stage: JobStatus;
  error_code: string | null;
  error_message: string | null;
  provider_usage: Record<string, number> | null;
  estimated_cost: number | null;
  created_at: string;
  updated_at: string;
}

export interface RemixJob {
  id: string;
  video_id: string;
  status: "queued" | "rendering" | "completed" | "failed";
  duration_ms: number | null;
  download_url: string | null;
  error_code: string | null;
}
