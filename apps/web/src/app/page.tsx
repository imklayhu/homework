"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { Clapperboard, ScanSearch, Scissors } from "lucide-react";

import { UploadPanel } from "@/components/UploadPanel";
import { uploadVideo } from "@/lib/api";


export default function Home() {
  const router = useRouter();
  return <main className="home-shell">
    <header className="topbar"><Link className="brand" href="/"><span className="brand-mark"><Clapperboard size={19} /></span><span>Framewise</span></Link><span className="product-tag">AI VIDEO STUDIO</span></header>
    <UploadPanel onUpload={async (file) => {
      const response = await uploadVideo(file);
      router.push(`/jobs/${response.job_id}`);
    }} />
    <section className="workflow-band" aria-label="处理流程">
      <div><span>01</span><ScanSearch size={20} /><strong>理解</strong><p>同步识别讲解、PPT 与演示画面</p></div>
      <div><span>02</span><Clapperboard size={20} /><strong>验证</strong><p>每个观点都能跳回原视频证据</p></div>
      <div><span>03</span><Scissors size={20} /><strong>重组</strong><p>选择片段、调整顺序、导出短片</p></div>
    </section>
    <footer className="home-footer"><span>Powered by Qwen VL + FFmpeg</span><span>视频仅用于本次分析</span></footer>
  </main>;
}
