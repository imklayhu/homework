"use client";

import { Check, LoaderCircle, RotateCcw, TriangleAlert } from "lucide-react";
import type { JobStatus } from "@/lib/types";


const stages: { key: JobStatus; label: string }[] = [
  { key: "uploaded", label: "上传完成" },
  { key: "preprocessing", label: "视频预处理" },
  { key: "understanding", label: "理解视频内容" },
  { key: "analyzing", label: "生成教学洞察" },
  { key: "completed", label: "分析完成" },
];

export function JobProgress({ status, errorMessage, onRetry }: { status: JobStatus; errorMessage?: string | null; onRetry?: () => void }) {
  if (status === "failed") {
    return <div className="job-error"><TriangleAlert size={20} /><div><strong>分析未完成</strong><p>{errorMessage ?? "处理遇到问题，请重试。"}</p></div>{onRetry && <button className="secondary-button" onClick={onRetry}><RotateCcw size={15} />重新分析</button>}</div>;
  }
  const current = stages.findIndex((stage) => stage.key === status);
  return <ol className="progress-list">{stages.map((stage, index) => {
    const done = index < current || status === "completed";
    const active = index === current && status !== "completed";
    return <li key={stage.key} className={done ? "done" : active ? "active" : ""} aria-current={active ? "step" : undefined}>
      <span className="stage-dot">{done ? <Check size={13} /> : active ? <LoaderCircle size={13} className="spin" /> : index + 1}</span>
      <span aria-current={active ? "step" : undefined}>{stage.label}</span>
    </li>;
  })}</ol>;
}
