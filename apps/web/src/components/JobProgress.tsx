"use client";

import { Check, LoaderCircle, RotateCcw, TriangleAlert } from "lucide-react";
import type { AnalysisJob, JobStatus } from "@/lib/types";


const stages: { key: JobStatus; label: string }[] = [
  { key: "uploaded", label: "上传完成" },
  { key: "preprocessing", label: "视频预处理" },
  { key: "understanding", label: "理解视频内容" },
  { key: "analyzing", label: "生成教学洞察" },
  { key: "completed", label: "分析完成" },
];

const timeFormatter = new Intl.DateTimeFormat("zh-CN", {
  hour12: false,
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
});

function UnderstandingProgress({ job }: { job: AnalysisJob }) {
  const nextSegment = Math.min(job.progress_current + 1, job.progress_total || 1);
  return <div className="understanding-progress">
    <div className="progress-summary">
      <strong>{job.progress_total ? `第 ${nextSegment}/${job.progress_total} 个片段` : "正在准备视频理解"}</strong>
      <span>{job.progress_percent}%</span>
    </div>
    <div className="progress-meter" role="progressbar" aria-label="视频理解进度" aria-valuemin={0} aria-valuemax={100} aria-valuenow={job.progress_percent}>
      <span className="progress-fill" style={{ width: `${job.progress_percent}%` }} />
    </div>
    <p className="progress-message">{job.progress_message ?? "正在准备视频理解"}</p>
    {job.logs.length > 0 && <ol className="job-log-list" aria-label="分析日志">
      {job.logs.map((log) => <li key={log.id} className={`job-log-${log.level}`}>
        <time dateTime={log.created_at}>{timeFormatter.format(new Date(log.created_at))}</time>
        <span>{log.message}</span>
      </li>)}
    </ol>}
  </div>;
}

export function JobProgress({ job, onRetry }: { job: AnalysisJob; onRetry?: () => void }) {
  const failed = job.status === "failed";
  const currentStatus = failed ? job.current_stage : job.status;
  const current = stages.findIndex((stage) => stage.key === currentStatus);
  const showUnderstandingProgress = currentStatus === "understanding" || (failed && (job.progress_total > 0 || job.logs.length > 0));

  return <>
    {failed && <div className="job-error"><TriangleAlert size={20} /><div><strong>分析未完成</strong><p>{job.error_message ?? "处理遇到问题，请重试。"}</p></div>{onRetry && <button className="secondary-button" onClick={onRetry}><RotateCcw size={15} />重新分析</button>}</div>}
    <ol className="progress-list">{stages.map((stage, index) => {
      const done = index < current || job.status === "completed";
      const active = index === current && job.status !== "completed";
      return <li key={stage.key} className={done ? "done" : active ? "active" : ""} aria-current={active ? "step" : undefined}>
        <span className="stage-dot">{done ? <Check size={13} /> : active ? <LoaderCircle size={13} className="spin" /> : index + 1}</span>
        <div className="stage-content"><span aria-current={active ? "step" : undefined}>{stage.label}</span>{stage.key === "understanding" && showUnderstandingProgress && <UnderstandingProgress job={job} />}</div>
      </li>;
    })}</ol>
  </>;
}
