import Link from "next/link";
import {
  ArrowUpRight,
  CheckCircle2,
  Clapperboard,
  Gauge,
  ScanSearch,
  Scissors,
  ShieldCheck,
} from "lucide-react";

const delivered = [
  ["上传与任务", "支持 MP4、MOV、WebM 上传，覆盖分片上传、处理进度和失败重试。"],
  ["多模态理解", "按 30 秒片段理解讲解、PPT 与演示画面，输出摘要、章节与教学观点。"],
  ["证据验证", "每条观点都能回跳原视频，让用户在剪辑前确认 AI 判断。"],
  ["Remix 生成", "选择观点、调整顺序，服务端生成可预览、下载的 MP4 短片。"],
];

const principles = [
  ["先证据，后生成", "AI 输出是带原视频证据的候选，而不是不可解释的结论。"],
  ["先稳定，后扩展", "优先优化完成率、等待时长和单次成本，而不是堆叠生成能力。"],
  ["全链路可观测", "埋点覆盖上传、任务、模型、失败和 Remix，用数据决定下一步。"],
];

const roadmap = [
  ["01", "可靠性与效率", "对象存储直传、异步任务队列、模型通道路由、自动恢复与成本控制。"],
  ["02", "内容质量", "ASR 字幕对齐、语义分段、切点微调与人工反馈闭环。"],
  ["03", "工作流与商业化", "多视频项目、团队审核、品牌模板、批量分发和机构账号计费。"],
];

export default function ProductPage() {
  return (
    <main className="product-shell">
      <header className="topbar">
        <Link className="brand" href="/">
          <span className="brand-mark"><Clapperboard size={19} /></span>
          <span>Framewise</span>
        </Link>
        <Link className="product-back" href="/">开始体验 <ArrowUpRight size={15} /></Link>
      </header>

      <section className="product-hero">
        <p className="eyebrow">AI VIDEO INSIGHT · PRODUCT CASE</p>
        <h1>把教育长视频变成可验证、可复用的内容资产</h1>
        <p>Framewise 面向课程创作者与内容运营人员，解决“知识点难定位、优质内容难二次分发”的问题。</p>
        <div className="product-hero-actions">
          <Link className="primary-button" href="/">体验视频分析</Link>
          <span>3–15 分钟视频 · 观点可回跳验证 · 支持 Remix 导出</span>
        </div>
      </section>

      <section className="product-section product-loop" aria-labelledby="loop-title">
        <div className="section-intro"><p className="eyebrow">END-TO-END LOOP</p><h2 id="loop-title">从理解到再创作的闭环</h2><p>不是只生成摘要，而是把 AI 理解结果转化为可以被用户确认和复用的内容单元。</p></div>
        <div className="product-loop-grid">
          <article><ScanSearch size={21} /><span>01</span><h3>理解</h3><p>识别讲解、课件和演示画面，提炼章节与教学观点。</p></article>
          <article><ShieldCheck size={21} /><span>02</span><h3>验证</h3><p>每个观点保留原视频时间证据，用户可一键回看确认。</p></article>
          <article><Scissors size={21} /><span>03</span><h3>重组</h3><p>选择片段、调整顺序，生成面向分发场景的短视频。</p></article>
        </div>
      </section>

      <section className="product-section" aria-labelledby="mvp-title">
        <div className="section-intro"><p className="eyebrow">SHIPPED MVP</p><h2 id="mvp-title">当前已经交付什么</h2></div>
        <div className="product-card-grid">
          {delivered.map(([title, text]) => <article className="product-card" key={title}><CheckCircle2 size={19} /><h3>{title}</h3><p>{text}</p></article>)}
        </div>
      </section>

      <section className="product-section product-decision" aria-labelledby="decision-title">
        <div className="section-intro"><p className="eyebrow">PRODUCT JUDGMENT</p><h2 id="decision-title">我做出的关键产品取舍</h2><p>教育内容的核心风险是错误理解和不可控等待，因此 MVP 先验证“结果可信、任务可完成、成本可承受”。</p></div>
        <div className="decision-list">
          {principles.map(([title, text], index) => <article key={title}><span>0{index + 1}</span><div><h3>{title}</h3><p>{text}</p></div></article>)}
        </div>
      </section>

      <section className="product-section product-measurement" aria-labelledby="measurement-title">
        <div className="section-intro"><p className="eyebrow">MEASUREMENT</p><h2 id="measurement-title">用什么指标判断产品有效</h2></div>
        <div className="measurement-grid">
          <article><Gauge size={19} /><h3>任务效率</h3><p>上传成功率、分析完成率、各阶段耗时、P50 / P95 时延。</p></article>
          <article><ShieldCheck size={19} /><h3>内容可信度</h3><p>观点证据点击率、用户编辑率、可用观点采纳率。</p></article>
          <article><Scissors size={19} /><h3>价值转化</h3><p>Remix 创建率、生成完成率、下载率与单条视频成本。</p></article>
        </div>
      </section>

      <section className="product-section roadmap-section" aria-labelledby="roadmap-title">
        <div className="section-intro"><p className="eyebrow">NEXT</p><h2 id="roadmap-title">三阶段产品路线</h2><p>优先解决稳定和效率，再提升内容质量，最后扩展团队工作流与商业化能力。</p></div>
        <ol className="roadmap-list">
          {roadmap.map(([number, title, text]) => <li key={number}><span>{number}</span><div><h3>{title}</h3><p>{text}</p></div></li>)}
        </ol>
      </section>

      <footer className="product-footer"><span>Framewise · AI Education Video Insight & Remix</span><Link href="/">返回体验 <ArrowUpRight size={14} /></Link></footer>
    </main>
  );
}
