"use client";

import { useRef, useState } from "react";
import { Download, Play } from "lucide-react";
import Link from "next/link";

import { InsightCard } from "./InsightCard";
import { RemixTray } from "./RemixTray";
import type { AnalysisPayload, Insight, RemixJob } from "@/lib/types";
import { createRemix, getRemix, remixUrl, videoUrl } from "@/lib/api";
import { formatDuration } from "@/lib/format";


export function VideoWorkspace({ videoId, result }: { videoId: string; result: AnalysisPayload }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [selected, setSelected] = useState<Insight[]>([]);
  const [remix, setRemix] = useState<RemixJob | null>(null);
  const [generating, setGenerating] = useState(false);

  function seek(ms: number) {
    if (!videoRef.current) return;
    videoRef.current.currentTime = ms / 1000;
    void videoRef.current.play();
  }
  function toggle(insight: Insight) {
    setSelected((items) => items.some((item) => item.id === insight.id) ? items.filter((item) => item.id !== insight.id) : [...items, insight]);
  }
  async function generate() {
    setGenerating(true);
    try {
      let job = await createRemix(videoId, selected.map((item) => item.id));
      setRemix(job);
      while (job.status === "queued" || job.status === "rendering") {
        await new Promise((resolve) => setTimeout(resolve, 1500));
        job = await getRemix(job.id);
        setRemix(job);
      }
    } finally { setGenerating(false); }
  }

  return <main className="workspace-shell">
    <header className="workspace-header"><Link className="brand" href="/"><span className="brand-mark">F</span><span>Framewise</span></Link><div><span className="status-pill">分析完成</span><Link className="secondary-button" href="/">新建分析</Link></div></header>
    <div className="workspace-grid">
      <section className="media-column">
        <video ref={videoRef} className="source-video" src={videoUrl(videoId)} controls preload="metadata" />
        <div className="summary-block"><span className="eyebrow">AI SUMMARY</span><h1>{result.summary}</h1><div className="chapter-list">{result.chapters.map((chapter, index) => <button key={chapter.id} onClick={() => seek(chapter.start_ms)}><span>{String(index + 1).padStart(2, "0")}</span><div><strong>{chapter.title}</strong><small>{formatDuration(chapter.start_ms)} · {chapter.summary}</small></div><Play size={14} /></button>)}</div></div>
        {remix?.status === "completed" && <section className="remix-output"><div><span className="eyebrow">REMIX READY</span><h2>你的观点短片已生成</h2></div><video src={remixUrl(remix.id)} controls /><a className="primary-button" href={remixUrl(remix.id)} download><Download size={16} />下载 MP4</a></section>}
      </section>
      <section className="insights-column"><div className="section-heading"><div><span className="eyebrow">TEACHING INSIGHTS</span><h2>教学观点</h2></div><strong>{result.insights.length}</strong></div>{result.insights.map((insight) => <InsightCard key={insight.id} insight={insight} selected={selected.some((item) => item.id === insight.id)} onSeek={seek} onToggle={() => toggle(insight)} />)}</section>
      <RemixTray insights={selected} onChange={setSelected} onGenerate={() => void generate()} generating={generating} />
    </div>
  </main>;
}
