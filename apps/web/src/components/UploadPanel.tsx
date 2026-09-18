"use client";

import { useRef, useState } from "react";
import { FileVideo, Upload, X } from "lucide-react";
import type { UploadProgress } from "@/lib/api";


const ALLOWED_TYPES = new Set(["video/mp4", "video/quicktime", "video/webm"]);

export function UploadPanel({ onUpload }: { onUpload: (file: File, onProgress: (progress: UploadProgress) => void) => Promise<void> | void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const [progress, setProgress] = useState<UploadProgress | null>(null);

  async function selectFile(file?: File) {
    if (!file) return;
    setError(null);
    if (!ALLOWED_TYPES.has(file.type)) {
      setError("仅支持 MP4、MOV 和 WebM 视频。 ");
      return;
    }
    if (file.size > 300 * 1024 * 1024) {
      setError("视频大小不能超过 300 MB。");
      return;
    }
    setFileName(file.name);
    setProgress(null);
    setUploading(true);
    try {
      await onUpload(file, setProgress);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "上传失败，请重试。");
    } finally {
      setUploading(false);
    }
  }

  return (
    <section className="upload-panel" aria-labelledby="upload-title">
      <div className="upload-copy">
        <span className="eyebrow">NEW ANALYSIS</span>
        <h1 id="upload-title">把一段课程，变成可验证的观点与短片</h1>
        <p>上传教育视频，AI 会同步理解讲解、PPT 与画面变化，并给出可以直接回看的证据片段。</p>
      </div>
      <div
        className="drop-zone"
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => { event.preventDefault(); void selectFile(event.dataTransfer.files[0]); }}
      >
        <input
          ref={inputRef}
          id="video-input"
          aria-label="选择视频"
          type="file"
          accept="video/mp4,video/quicktime,video/webm,.mp4,.mov,.webm"
          onChange={(event) => void selectFile(event.target.files?.[0])}
          hidden
        />
        <div className="upload-icon"><FileVideo size={28} strokeWidth={1.7} /></div>
        <div>
          <strong>{uploading ? (progress ? `正在上传 ${progress.percent}%（${progress.uploadedChunks}/${progress.totalChunks}）` : "正在准备上传...") : fileName ?? "拖入课程视频"}</strong>
          <span>MP4、MOV、WebM · 3–15 分钟 · 最大 300 MB</span>
        </div>
        <button className="primary-button" type="button" disabled={uploading} onClick={() => inputRef.current?.click()}>
          <Upload size={17} />{uploading ? "上传中" : "选择视频"}
        </button>
      </div>
      {error && <div className="error-banner"><X size={16} />{error}</div>}
    </section>
  );
}
