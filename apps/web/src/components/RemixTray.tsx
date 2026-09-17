"use client";

import { ArrowDown, ArrowUp, Film, Trash2 } from "lucide-react";
import type { Insight } from "@/lib/types";
import { formatDuration } from "@/lib/format";


export function RemixTray({ insights, onChange, onGenerate, generating = false }: { insights: Insight[]; onChange: (next: Insight[]) => void; onGenerate: () => void; generating?: boolean }) {
  const duration = insights.reduce((total, item) => total + item.end_ms - item.start_ms, 0);
  function move(index: number, offset: number) {
    const target = index + offset;
    if (target < 0 || target >= insights.length) return;
    const next = [...insights];
    [next[index], next[target]] = [next[target], next[index]];
    onChange(next);
  }
  return <aside className="remix-tray">
    <div className="tray-heading"><div><span className="eyebrow">REMIX QUEUE</span><h2>片段编排</h2></div><strong>{formatDuration(duration)}</strong></div>
    {insights.length === 0 ? <div className="tray-empty"><Film size={22} /><p>从右侧观点中加入片段</p></div> : <ol className="remix-list">{insights.map((item, index) => <li key={item.id} data-testid="remix-item">
      <span className="order-number">{String(index + 1).padStart(2, "0")}</span><div><strong>{item.title}</strong><span>{formatDuration(item.end_ms - item.start_ms)}</span></div>
      <div className="icon-actions">
        <button aria-label={`上移${item.title}`} title="上移" disabled={index === 0} onClick={() => move(index, -1)}><ArrowUp size={15} /></button>
        <button aria-label={`下移${item.title}`} title="下移" disabled={index === insights.length - 1} onClick={() => move(index, 1)}><ArrowDown size={15} /></button>
        <button aria-label={`移除${item.title}`} title="移除" onClick={() => onChange(insights.filter((entry) => entry.id !== item.id))}><Trash2 size={15} /></button>
      </div>
    </li>)}</ol>}
    <button className="primary-button full-width" disabled={!insights.length || duration > 180_000 || generating} onClick={onGenerate}><Film size={17} />{generating ? "正在生成" : "生成 Remix"}</button>
    <p className="tray-note">最多 8 段 / 3 分钟，切点已加入语句缓冲</p>
  </aside>;
}
