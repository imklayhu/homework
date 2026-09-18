import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { UploadPanel } from "@/components/UploadPanel";


test("shows upload constraints and rejects an unsupported file", async () => {
  const upload = vi.fn();
  render(<UploadPanel onUpload={upload} />);

  expect(screen.getByText(/3–15 分钟/)).toBeInTheDocument();
  const input = screen.getByLabelText("选择视频");
  await userEvent.upload(input, new File(["bad"], "lesson.mp4", { type: "application/octet-stream" }));

  expect(screen.getByText(/仅支持 MP4、MOV 和 WebM/)).toBeInTheDocument();
  expect(upload).not.toHaveBeenCalled();
});


test("uploads a supported video", async () => {
  const upload = vi.fn().mockResolvedValue(undefined);
  render(<UploadPanel onUpload={upload} />);
  const file = new File(["video"], "lesson.mp4", { type: "video/mp4" });

  await userEvent.upload(screen.getByLabelText("选择视频"), file);

  expect(upload).toHaveBeenCalledWith(file, expect.any(Function));
});

test("shows confirmed chunk upload progress", async () => {
  const upload = vi.fn(async (_file: File, onProgress: (value: {percent:number;uploadedChunks:number;totalChunks:number}) => void) => {
    onProgress({ percent: 48, uploadedChunks: 6, totalChunks: 13 });
    await new Promise(() => undefined);
  });
  render(<UploadPanel onUpload={upload} />);
  await userEvent.upload(screen.getByLabelText("选择视频"), new File(["video"], "lesson.mp4", { type: "video/mp4" }));
  expect(await screen.findByText("正在上传 48%（6/13）")).toBeInTheDocument();
});
