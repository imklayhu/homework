"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

import { JobProgress } from "@/components/JobProgress";
import { VideoWorkspace } from "@/components/VideoWorkspace";
import { getJob, getResult, retryJob } from "@/lib/api";
import type { AnalysisJob, AnalysisPayload } from "@/lib/types";


export default function JobPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [job, setJob] = useState<AnalysisJob | null>(null);
  const [result, setResult] = useState<AnalysisPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const next = await getJob(jobId);
      setJob(next);
      if (next.status === "completed") setResult(await getResult(jobId));
      return next.status;
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "无法读取任务状态。");
      return "failed";
    }
  }, [jobId]);

  useEffect(() => {
    let stopped = false;
    async function poll() {
      const status = await refresh();
      if (!stopped && status !== "completed" && status !== "failed") window.setTimeout(poll, 2000);
    }
    void poll();
    return () => { stopped = true; };
  }, [refresh]);

  if (job?.status === "completed" && result) return <VideoWorkspace videoId={job.video_id} result={result} />;
  return <main className="processing-shell"><Link className="brand" href="/"><span className="brand-mark">F</span><span>Framewise</span></Link><section className="processing-panel"><span className="eyebrow">ANALYSIS IN PROGRESS</span><h1>正在把视频拆成可验证的知识片段</h1><p>页面可以保持打开，完成后会自动进入分析工作台。</p>{job ? <JobProgress status={job.status} errorMessage={job.error_message} onRetry={job.status === "failed" ? async () => { await retryJob(jobId); setError(null); void refresh(); } : undefined} /> : <div className="loading-line">正在读取任务...</div>}{error && <p className="inline-error">{error}</p>}</section></main>;
}
