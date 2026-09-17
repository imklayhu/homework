"use client";

import { Eye, MessageSquareText, Plus, Play, Check } from "lucide-react";
import type { Insight } from "@/lib/types";
import { formatConfidence, formatDuration } from "@/lib/format";


export function InsightCard({ insight, selected, onSeek, onToggle }: { insight: Insight; selected: boolean; onSeek: (ms: number) => void; onToggle: () => void }) {
  return <article className={`insight-card ${selected ? "selected" : ""}`}>
    <div className="insight-meta"><button className="timestamp-button" onClick={() => onSeek(insight.start_ms)}><Play size={13} fill="currentColor" />{formatDuration(insight.start_ms)}–{formatDuration(insight.end_ms)}</button><span>{formatConfidence(insight.confidence)} 置信度</span></div>
    <h3>{insight.title}</h3><p className="insight-explanation">{insight.explanation}</p>
    <div className="evidence-list">
      {insight.transcript_evidence && <div><MessageSquareText size={15} /><p>{insight.transcript_evidence}</p></div>}
      {insight.visual_evidence && <div><Eye size={15} /><p>{insight.visual_evidence}</p></div>}
    </div>
    <div className="insight-footer"><span>{insight.remix_reason}</span><button className={selected ? "selected-button" : "secondary-button"} onClick={onToggle}>{selected ? <Check size={15} /> : <Plus size={15} />}{selected ? "已加入" : "加入 Remix"}</button></div>
  </article>;
}
