# 百炼模型可用性检查

检查日期：2026-09-17

## 检查范围

- 从项目根目录 `.env` 读取工作空间与 ON_DEMAND 两组连接配置；
- 未输出、记录或写入 API Key；
- 分别调用两组配置地址的 `/models` 接口；
- 对候选视频模型执行一次真实 `video_url` 能力探针。

## 两个端点的检查结果

| 端点 | HTTP 状态 | 模型数 | 与本项目相关的结论 |
|---|---:|---:|---|
| 原工作空间 | 200 | 14 | 没有 Qwen VL 和批量文件 ASR；`qwen3.8-flash` 已实测可理解视频 |
| ON_DEMAND | 200 | 253 | 补齐 `qwen3-vl-flash`、`qwen3-vl-plus` 和非实时 ASR 候选 |

模型列表可见不等于推理账号当前可用。收尾评测期间，ON_DEMAND 推理请求返回 HTTP 400 / `Arrearage`；应用因此自动回退到原工作空间的 `qwen3.8-flash`。本文不记录两组 Base URL 或任何密钥。

### 原工作空间返回的模型

```text
deepseek-v4-flash-0731
deepseek-v4-pro
deepseek-v4.1-flash
glm-5.2
glm-5.3
qwen-audio-3.0-realtime-plus
qwen-audio-3.0-tts-plus
qwen3.6-flash
qwen3.7-max
qwen3.7-plus
qwen3.8-flash
qwen3.8-max
wan2.7-image
wan2.7-image-pro
```

### ON_DEMAND 补齐的关键模型

- 视频理解：`qwen3-vl-flash`、`qwen3-vl-plus` 及其日期版本；
- 可选视频模型：`qwen-vl-max`、`qwen-vl-plus`、若干 `qwen3.5-omni-*`；
- 非实时 ASR：`qwen3-asr-flash-2026-02-10`；
- 其他 ASR：`qwen-audio-3.0-asr-flash`、`fun-asr-flash-2026-06-15` 及若干实时型号；
- 两个端点均未返回 `paraformer-v2`。

## 原计划模型检查

| 原计划模型 | 原工作空间 | ON_DEMAND | 结论 |
|---|---:|---:|---|
| `qwen3-vl-flash` | 否 | 是 | 改为默认视频理解与洞察模型 |
| `qwen3-vl-plus` | 否 | 是 | 作为低置信度兜底 |
| `paraformer-v2` | 否 | 否 | 不再作为可直接使用的默认模型 |
| `qwen3-asr-flash-2026-02-10` | 否 | 是 | 可做低成本非实时转写，但官方资料未确认句级/词级时间戳 |

## 视频能力实测

对 `qwen3.8-flash` 发送公网 MP4，使用 OpenAI 兼容接口的 `video_url` 输入和 0.5 FPS：

- HTTP 状态：200；
- 模型成功识别视频内容；
- 模型成功返回 `HH:mm:ss` 时间点；
- 本次探针使用 770 video tokens、68 text tokens；
- 说明当前账号的 `qwen3.8-flash` 确实开放了视频理解，不需要模型名称中包含 `vl`。

因此 MVP 的运行时路由为：

```text
主通道：ON_DEMAND / qwen3-vl-flash
端点异常回退：原工作空间 / qwen3.8-flash
```

ON_DEMAND 的 `qwen3-vl-flash` 曾完成真实公网 MP4 探针：HTTP 200，正确描述画面并返回 `00:03` 时间点；本次使用 1,026 video tokens、28 text input tokens 和 43 completion tokens。这证明模型能力满足需求，但不代表账号余额持续可用。当前正式评测实际由回退通道 `qwen3.8-flash` 完成。

## ASR 缺口与替代方式

`qwen3-asr-flash-2026-02-10` 是 ON_DEMAND 中最接近需求的非实时转写模型，可用于获取字幕文本；但当前官方模型页没有确认它能稳定返回 Remix 所需的句级/词级时间戳。`qwen-audio-3.0-realtime-plus` 是实时语音交互模型，也不应当作批量时间轴 ASR 使用。

按成本和三天工期排序：

### 方案 A：只用 `qwen3-vl-flash`（Homework 首选）

- 由模型直接输出章节、观点和候选片段时间范围；
- 片段首尾各增加约 1–1.5 秒缓冲；
- 用户在 Remix 前预览片段并确认；
- 优点：零新增账号、链路最短、成本最低；
- 缺点：不是词级时间戳，剪辑边界精度有限。

对于本次 Homework，产品价值在于“原生视频理解 → 可验证观点 → 用户确认 → Remix”，该精度通常足够完成 MVP。

### 方案 B：本地 Whisper 时间轴（推荐增强）

- 使用 `faster-whisper`、`whisper.cpp` 或 Apple Silicon 上的 `mlx-whisper`；
- 选用 `base` 或 `small` 模型生成 segment/word 时间戳；
- API 成本为 0；
- 优点：提供真实时间轴，保留混合架构；
- 缺点：首次下载模型，部署时需要 CPU/内存和处理时间。

如果本机为 Apple Silicon，Homework 本地开发优先考虑 `mlx-whisper`；若希望开发和 Linux 部署保持一致，优先考虑 `faster-whisper`。

### 方案 C：使用 ON_DEMAND ASR 获取文本

- 使用 `qwen3-asr-flash-2026-02-10` 生成中文转写；
- 视频模型的候选时间范围仍用于剪辑定位；
- 优点：已经出现在 ON_DEMAND 列表，托管调用链简单；
- 缺点：时间戳粒度未确认，不能把精确切点建立在未经实测的能力上。

## 最终实现

当前代码采用：

```text
视频理解与观点分析：ON_DEMAND / qwen3-vl-flash
供应商错误回退：原工作空间 / qwen3.8-flash
可选转写：暂不启用
候选片段时间：实际执行的视频理解模型生成 + 首尾缓冲 + 用户预览确认
Remix：FFmpeg
```

3 条不同长视频样本均未显示需要 ASR 才能修正的明显断句，因此不扩展本地 Whisper。自动回退仅处理模型供应商错误，不吞掉业务校验错误。

## 价格参考

原工作空间备选模型 `qwen3.8-flash` 的北京地域参考价格为：

- 输入：约 ¥0.8 / 百万 Token；
- 输出：约 ¥2.7 / 百万 Token；
- 新用户额度：100 万 Token（以控制台实际显示为准）。

本次短视频探针约 1,179 总 Token，因此单次探针成本远低于 1 分钱。3 条 3:48–3:59 样本的长视频实测为 ¥0.1169–¥0.1225/条，平均约 ¥0.120；5 次有效运行合计约 ¥0.600。更长视频仍应以接口返回的 usage 做实测，不用文件大小直接推算 Token。

官方参考：

- <https://help.aliyun.com/zh/model-studio/vision>
- <https://help.aliyun.com/zh/model-studio/models>
- <https://help.aliyun.com/zh/model-studio/model-pricing>
- <https://help.aliyun.com/zh/model-studio/qwen3-asr-flash>
