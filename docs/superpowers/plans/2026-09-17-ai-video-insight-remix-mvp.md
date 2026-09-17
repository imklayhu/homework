# AI Video Insight Remix MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在三天内实现一个可本地运行的 Web MVP：上传 3–15 分钟教育视频，获得带时间证据的摘要、章节和教学观点，选择并排序观点后用 FFmpeg 生成可预览、下载的 Remix MP4。

**Architecture:** 使用 `apps/web` 的 Next.js 前端和 `apps/api` 的 FastAPI 后端。后端以 SQLite 持久化任务与结构化结果，本地目录保存原视频和输出；后台线程执行 ffprobe、百炼原生视频理解、确定性校验和 FFmpeg Remix。模型适配层默认调用 ON_DEMAND 的 `qwen3-vl-flash`，可选调用 `qwen3-asr-flash-2026-02-10` 获取转写文本，切点仍以 VL 候选时间段、边界缓冲和用户预览为准。

**Tech Stack:** Next.js 15、React、TypeScript、Tailwind CSS、Vitest、Playwright；Python 3.12、FastAPI、SQLModel/SQLite、Pydantic v2、httpx、pytest；FFmpeg/ffprobe；OpenAI-compatible 百炼 API。

---

## 0. 交付边界与验收门槛

### P0 必须完成

- 上传 MP4/MOV/WebM，限制 300 MB、3–15 分钟；
- 展示真实任务阶段和失败原因；
- `qwen3-vl-flash` 返回摘要、章节、观点、视觉/语音证据和候选时间范围；
- 点击章节或观点可跳转原视频；
- 用户选择、排序观点，预览总时长；
- FFmpeg 按顺序裁剪、拼接为 MP4；
- 刷新页面后可通过任务 URL 恢复结果；
- 至少 3 个真实教育视频完成评测，记录耗时、usage、估算费用与 badcase；
- 内置一个已完成样例，作为现场演示兜底。

### 明确不做

- 登录、支付、团队协作、云端部署；
- WebSocket、Redis、Celery、对象存储；
- 生成式视频、字幕烧录、9:16 模板、复杂轨道编辑器；
- 自动发布或多视频混剪；
- 在未实测前承诺 ASR 具有词级时间戳。

### Day 1 / Day 2 / Day 3 闸门

- Day 1：真实视频能得到合法 JSON，并能按一个观点裁出正确片段；失败则冻结 UI 扩展。
- Day 2：新用户能独立走通上传、分析、选择、排序、生成和下载。
- Day 3 中午：功能冻结，只修复 P0 阻断问题和演示 badcase。

---

## 1. 文件结构

```text
homework/
├── .env                         # 已存在，只保存真实密钥，不提交
├── .env.example                 # 前后端配置键名与安全默认值
├── Makefile                     # install/dev/test/verify 命令
├── README.md                    # 本地启动、演示路径、限制、架构和成本
├── apps/
│   ├── api/
│   │   ├── pyproject.toml
│   │   ├── app/
│   │   │   ├── main.py          # FastAPI 生命周期、CORS、路由注册
│   │   │   ├── config.py        # 环境变量和路径配置
│   │   │   ├── db.py            # SQLite engine/session/init
│   │   │   ├── models.py        # Video/AnalysisJob/AnalysisResult/RemixJob
│   │   │   ├── schemas.py       # API 与模型输出 Pydantic 合同
│   │   │   ├── errors.py        # 稳定错误码和用户文案
│   │   │   ├── routes/
│   │   │   │   ├── health.py
│   │   │   │   ├── videos.py
│   │   │   │   ├── jobs.py
│   │   │   │   └── remixes.py
│   │   │   └── services/
│   │   │       ├── media.py     # ffprobe、文件校验、音频/代理处理
│   │   │       ├── bailian.py   # ON_DEMAND OpenAI-compatible adapter
│   │   │       ├── prompts.py   # 版本化分析提示词
│   │   │       ├── validator.py # schema、时间范围、缓冲、重叠校验
│   │   │       ├── analysis.py  # 分析状态机与有限重试
│   │   │       └── remix.py     # 安全 FFmpeg 裁剪和拼接
│   │   └── tests/
│   │       ├── fixtures/
│   │       ├── test_health.py
│   │       ├── test_media.py
│   │       ├── test_validator.py
│   │       ├── test_analysis.py
│   │       ├── test_video_api.py
│   │       └── test_remix.py
│   └── web/
│       ├── package.json
│       ├── next.config.ts
│       ├── src/
│       │   ├── app/page.tsx
│       │   ├── app/jobs/[jobId]/page.tsx
│       │   ├── app/globals.css
│       │   ├── components/UploadPanel.tsx
│       │   ├── components/JobProgress.tsx
│       │   ├── components/VideoWorkspace.tsx
│       │   ├── components/InsightCard.tsx
│       │   ├── components/RemixTray.tsx
│       │   ├── lib/api.ts
│       │   ├── lib/types.ts
│       │   └── lib/format.ts
│       └── tests/
│           ├── UploadPanel.test.tsx
│           ├── JobProgress.test.tsx
│           ├── RemixTray.test.tsx
│           └── happy-path.spec.ts
├── data/                         # gitignored 本地 SQLite、上传与输出
├── samples/
│   ├── README.md                 # 样例来源与授权说明
│   └── demo-result.json          # 已完成演示兜底结果
└── docs/
    ├── evaluation.md             # 3–5 条样例评测表与 badcase
    └── superpowers/             # 已确认的设计与本实施计划
```

文件边界原则：路由只做 HTTP 参数转换；模型供应商逻辑只在 `bailian.py`；业务状态只在 `analysis.py`；所有 FFmpeg 参数只由 `media.py`/`remix.py` 生成；前端只消费稳定 API 类型。

---

## Task 1：建立可重复运行的项目骨架

**Files:**
- Create: `.env.example`
- Modify: `.gitignore`
- Create: `Makefile`
- Create: `apps/api/pyproject.toml`
- Create: `apps/api/app/__init__.py`
- Create: `apps/api/app/config.py`
- Create: `apps/api/app/main.py`
- Create: `apps/api/app/routes/health.py`
- Create: `apps/api/tests/test_health.py`
- Create: `apps/web/*`（由 create-next-app 生成后精简）

- [ ] **Step 1：检查本机前置依赖并记录版本**

Run:

```bash
node --version
pnpm --version
python3 --version
ffmpeg -version | head -1
ffprobe -version | head -1
```

Expected: Node 20+、pnpm 9+、Python 3.11+，FFmpeg 与 ffprobe 均可执行。缺失时先安装，不进入模型开发。

- [ ] **Step 2：写健康检查的失败测试**

```python
from fastapi.testclient import TestClient
from app.main import app

def test_health_returns_ok():
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

Run: `cd apps/api && uv run pytest tests/test_health.py -q`

Expected: FAIL，提示 `app.main` 或路由不存在。

- [ ] **Step 3：实现配置和最小 FastAPI 应用**

`config.py` 必须使用 `pydantic-settings`，定义 `data_dir`、`database_url`、`cors_origin`、两组百炼配置、模型名、上传限制和 `enable_asr`；不得在日志输出密钥或 Base URL。

```python
class Settings(BaseSettings):
    data_dir: Path = Path("../../data")
    database_url: str = "sqlite:///../../data/app.db"
    cors_origin: str = "http://localhost:3000"
    on_demand_api_key: SecretStr | None = None
    on_demand_base_url: str | None = None
    video_understanding_model: str = "qwen3-vl-flash"
    fallback_video_model: str = "qwen3-vl-plus"
    transcription_model: str = "qwen3-asr-flash-2026-02-10"
    enable_asr: bool = False
    max_upload_bytes: int = 300 * 1024 * 1024
    min_duration_seconds: int = 180
    max_duration_seconds: int = 900
```

`GET /api/health` 只返回 `{"status":"ok"}`。应用启动时创建 `data/uploads`、`data/remixes`、`data/tmp`。

- [ ] **Step 4：运行后端测试并创建前端骨架**

Run:

```bash
cd apps/api && uv run pytest tests/test_health.py -q
cd ../.. && pnpm create next-app apps/web --ts --tailwind --eslint --app --src-dir --use-pnpm --import-alias '@/*'
```

Expected: health test PASS；`pnpm --dir apps/web lint` PASS。

- [ ] **Step 5：添加安全配置样例和统一命令**

`.env.example` 仅包含空值或安全默认值：

```dotenv
ON_DEMAND_API_KEY=
ON_DEMAND_BASE_URL=
BAILIAN_BASE_URL=
API_KEY=
VIDEO_UNDERSTANDING_MODEL=qwen3-vl-flash
FALLBACK_VIDEO_MODEL=qwen3-vl-plus
TRANSCRIPTION_MODEL=qwen3-asr-flash-2026-02-10
ENABLE_ASR=false
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

`.gitignore` 增加 `data/`、`.venv/`、`node_modules/`、`.next/`、`__pycache__/`、`.pytest_cache/`、Playwright 输出。Makefile 提供 `install`、`dev-api`、`dev-web`、`test-api`、`test-web`、`verify`。

- [ ] **Step 6：提交骨架**

```bash
git add .env.example .gitignore Makefile apps/api apps/web
git commit -m "chore: scaffold web and api applications"
```

---

## Task 2：定义领域合同与 SQLite 持久化

**Files:**
- Create: `apps/api/app/db.py`
- Create: `apps/api/app/models.py`
- Create: `apps/api/app/schemas.py`
- Create: `apps/api/tests/test_models.py`
- Create: `apps/web/src/lib/types.ts`

- [ ] **Step 1：写模型合同失败测试**

测试必须覆盖：合法 insight 可解析；`start_ms >= end_ms` 失败；confidence 超出 0–1 失败；空 chapters/insights 失败；Job 枚举只接受约定状态。

```python
def test_insight_rejects_reversed_time_range():
    with pytest.raises(ValidationError):
        Insight(id="i1", title="x", explanation="x", start_ms=2000,
                end_ms=1000, transcript_evidence="", visual_evidence="",
                evidence_types=["visual"], confidence=.8, remix_reason="x")
```

Run: `cd apps/api && uv run pytest tests/test_models.py -q`

Expected: FAIL，因为 schema 尚不存在。

- [ ] **Step 2：实现稳定的 API 类型**

定义：

```python
class JobStatus(StrEnum):
    UPLOADED = "uploaded"
    PREPROCESSING = "preprocessing"
    UNDERSTANDING = "understanding"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"

class AnalysisPayload(BaseModel):
    summary: str = Field(min_length=1)
    chapters: list[Chapter] = Field(min_length=1, max_length=12)
    insights: list[Insight] = Field(min_length=1, max_length=12)
```

`Chapter` 和 `Insight` 使用 `model_validator` 保证 `start_ms < end_ms`。`AnalysisJobRead` 包含状态、阶段、错误码、用户错误文案、usage、estimated_cost；不得暴露内部异常堆栈。

- [ ] **Step 3：实现四张最小表和数据库生命周期**

按设计创建 `Video`、`AnalysisJob`、`AnalysisResult`、`RemixJob`。复杂结构存 JSON 字符串；所有 ID 使用 UUID 字符串；时间使用 UTC；测试通过临时 SQLite 覆盖依赖。

- [ ] **Step 4：生成前端镜像类型**

`types.ts` 定义与 API JSON 完全一致的 `JobStatus`、`Video`、`Chapter`、`Insight`、`AnalysisPayload`、`AnalysisJob`、`RemixJob`。时间统一为毫秒，前端不得自行猜测秒/毫秒。

- [ ] **Step 5：验证并提交**

Run: `cd apps/api && uv run pytest tests/test_models.py -q`

Expected: PASS。

```bash
git add apps/api/app/db.py apps/api/app/models.py apps/api/app/schemas.py apps/api/tests/test_models.py apps/web/src/lib/types.ts
git commit -m "feat: define analysis domain and persistence"
```

---

## Task 3：实现上传、ffprobe 预检和安全文件访问

**Files:**
- Create: `apps/api/app/errors.py`
- Create: `apps/api/app/services/media.py`
- Create: `apps/api/app/routes/videos.py`
- Create: `apps/api/tests/test_media.py`
- Create: `apps/api/tests/test_video_api.py`

- [ ] **Step 1：创建测试视频 fixture**

Run:

```bash
mkdir -p apps/api/tests/fixtures
ffmpeg -y -f lavfi -i testsrc=size=640x360:rate=25 -f lavfi -i sine=frequency=1000 -t 4 -c:v libx264 -c:a aac apps/api/tests/fixtures/sample.mp4
```

Expected: 生成带音视频轨的 4 秒 MP4，仅用于单元测试；测试配置将时长边界覆盖为 1–10 秒。

- [ ] **Step 2：写失败测试**

覆盖：ffprobe 返回时长/尺寸/编码；拒绝不支持扩展名；拒绝超限文件；拒绝时长越界；保存名由 UUID 生成且不包含原文件路径；`GET /api/videos/{id}/content` 只访问数据库登记路径。

- [ ] **Step 3：实现参数数组形式的 ffprobe**

```python
command = [
    "ffprobe", "-v", "error", "-print_format", "json",
    "-show_format", "-show_streams", str(path),
]
result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=True)
```

不得使用 `shell=True`。将异常映射为 `INVALID_VIDEO`、`VIDEO_TOO_SHORT`、`VIDEO_TOO_LONG`、`FILE_TOO_LARGE`、`UNSUPPORTED_FORMAT`。

- [ ] **Step 4：实现上传 API**

`POST /api/videos` 流式写入临时文件，验证后原子移动至 `data/uploads/{video_id}/source.{ext}`，创建 Video 和 AnalysisJob，返回 202：

```json
{"video_id":"6acfdca2-9f52-4eba-8a1d-ea93d33f0ec4","job_id":"23f6d7c2-748d-4947-b5bb-2a821e36dd8e","status":"uploaded"}
```

不要在本任务启动后台模型调用；先保证媒体入口可靠。

- [ ] **Step 5：运行测试并提交**

Run: `cd apps/api && uv run pytest tests/test_media.py tests/test_video_api.py -q`

Expected: PASS，且临时目录测试结束后为空。

```bash
git add apps/api/app/errors.py apps/api/app/services/media.py apps/api/app/routes/videos.py apps/api/tests
git commit -m "feat: add validated video upload pipeline"
```

---

## Task 4：接入 Qwen 原生视频理解与严格 JSON 输出

**Files:**
- Create: `apps/api/app/services/prompts.py`
- Create: `apps/api/app/services/bailian.py`
- Create: `apps/api/tests/test_bailian.py`
- Create: `apps/api/tests/fixtures/qwen-response.json`

- [ ] **Step 1：固定 prompt v1 与输出 Schema**

系统提示必须包含：仅根据视频内容作答；时间使用毫秒整数；每条观点需独立完整、15–90 秒；证据区分 transcript/visual；无法确认时降低 confidence；禁止 Markdown；输出严格匹配 `AnalysisPayload`。Prompt 常量命名为 `ANALYSIS_PROMPT_VERSION = "qwen-video-v1"`。

- [ ] **Step 2：写 adapter 失败测试**

使用 `httpx.MockTransport` 覆盖：正确构造 `video_url` 内容；解析 usage；200 合法 JSON；429/5xx 可重试；401 不重试；超时映射为 `MODEL_TIMEOUT`；非法 JSON 只执行一次修复请求；日志不包含 key。

- [ ] **Step 3：实现异步百炼 adapter**

接口保持供应商无关：

```python
class VideoUnderstandingAdapter(Protocol):
    async def analyze(self, video_url: str, duration_ms: int) -> ModelAnalysisResult:
        raise NotImplementedError

@dataclass
class ModelAnalysisResult:
    payload: AnalysisPayload
    usage: dict[str, int]
    model: str
    prompt_version: str
```

调用 `${ON_DEMAND_BASE_URL}/chat/completions`，Bearer 使用 SecretStr，timeout 设置连接 10 秒、整体 180 秒。网络/429/5xx 指数退避最多 2 次；测试注入 `sleep` 以避免真实等待。

- [ ] **Step 4：验证真实模型 smoke test**

新增默认跳过的 `@pytest.mark.live` 测试，读取 `.env` 和一个小型公网 MP4，只断言 HTTP 成功、Schema 合法、至少一个 insight、usage 非空。普通 `pytest` 不得产生费用。

Run:

```bash
cd apps/api && uv run pytest tests/test_bailian.py -q
uv run pytest -m live tests/test_bailian.py -q
```

Expected: mock 测试全部 PASS；live 测试在配置存在时 PASS，并记录耗时和 usage，不记录密钥/Base URL。

- [ ] **Step 5：提交模型适配层**

```bash
git add apps/api/app/services/prompts.py apps/api/app/services/bailian.py apps/api/tests/test_bailian.py apps/api/tests/fixtures/qwen-response.json
git commit -m "feat: add qwen native video analysis adapter"
```

---

## Task 5：实现确定性校验、边界缓冲和成本记录

**Files:**
- Create: `apps/api/app/services/validator.py`
- Create: `apps/api/app/services/cost.py`
- Create: `apps/api/tests/test_validator.py`
- Create: `apps/api/tests/test_cost.py`

- [ ] **Step 1：写边界案例测试**

覆盖：负时间裁为 0；超过视频时长裁到 duration；首尾各加 1,000 ms；缓冲后仍 `start < end`；短于 5 秒或长于 120 秒拒绝；高度重叠观点标记 warning 而不静默删除；章节按开始时间排序；ID 重复失败。

```python
def test_padding_is_clamped_to_video_bounds():
    result = normalize_range(500, 9_500, duration_ms=10_000, padding_ms=1_000)
    assert result == (0, 10_000)
```

- [ ] **Step 2：实现纯函数校验器**

`validate_and_normalize(payload, duration_ms)` 返回 `ValidatedAnalysis(payload, warnings)`；不修改输入对象，不调用数据库或模型。失败使用稳定错误码 `INVALID_MODEL_OUTPUT`。

- [ ] **Step 3：实现透明成本估算**

以 usage 原样保存；成本计算器使用配置单价，不把价格散落在业务代码中。若供应商 usage 缺字段，`estimated_cost` 为 null 而非伪造精确值。ASR 按秒计算并单独列项。

- [ ] **Step 4：运行测试并提交**

Run: `cd apps/api && uv run pytest tests/test_validator.py tests/test_cost.py -q`

Expected: PASS。

```bash
git add apps/api/app/services/validator.py apps/api/app/services/cost.py apps/api/tests
git commit -m "feat: validate timestamps and track model cost"
```

---

## Task 6：完成后台分析状态机与查询 API

**Files:**
- Create: `apps/api/app/services/analysis.py`
- Create: `apps/api/app/routes/jobs.py`
- Create: `apps/api/tests/test_analysis.py`
- Modify: `apps/api/app/routes/videos.py`
- Modify: `apps/api/app/main.py`

- [ ] **Step 1：写状态机失败测试**

覆盖成功路径 `uploaded → preprocessing → understanding → analyzing → completed`；模型失败进入 `failed` 并记录 failed_stage；重试只重跑分析不重复上传；重复启动同一 completed job 无副作用；数据库保存 prompt/model/usage/成本。

- [ ] **Step 2：实现后台编排**

上传成功后通过 FastAPI `BackgroundTasks` 调用 `run_analysis(job_id)`。每个阶段先提交状态，再执行工作；捕获已知异常映射用户文案；内部 detail 只写服务端日志。MVP 单进程运行，并在 README 明确多进程部署需迁移队列。

- [ ] **Step 3：实现查询与重试端点**

```text
GET  /api/jobs/{job_id}
GET  /api/jobs/{job_id}/result
POST /api/jobs/{job_id}/retry
```

未完成时 result 返回 409；不存在返回 404；只有 failed 可 retry；completed 重试返回 409，避免重复花费。

- [ ] **Step 4：增加模型不可用的演示降级**

配置 `DEMO_MODE=true` 时仅允许对内置 demo video hash 读取 `samples/demo-result.json`，UI 明确标记“演示样例”；不得对任意上传伪装成真实分析结果。

- [ ] **Step 5：运行集成测试并提交**

Run: `cd apps/api && uv run pytest tests/test_analysis.py tests/test_video_api.py -q`

Expected: PASS；测试 adapter 不触发网络。

```bash
git add apps/api/app/services/analysis.py apps/api/app/routes apps/api/app/main.py apps/api/tests
git commit -m "feat: orchestrate persistent video analysis jobs"
```

---

## Task 7：验证 Day 1 风险——真实视频到单片段

**Files:**
- Create: `scripts/smoke_analysis.py`
- Create: `scripts/smoke_clip.py`
- Create: `docs/day1-validation.md`

- [ ] **Step 1：运行真实 1–3 分钟教育样例分析**

脚本上传视频、轮询任务、保存脱敏 JSON，输出：总耗时、模型、video/input/output tokens、观点数量、估算成本。不得输出凭据和 Base URL。

Run: `uv run python scripts/smoke_analysis.py /absolute/path/to/sample.mp4`

Expected: job completed，至少 1 个合法 insight。

- [ ] **Step 2：按第一个 insight 裁剪验证片段**

使用参数数组调用 FFmpeg，H.264/AAC、`+faststart`，输出到临时目录。

Run: `uv run python scripts/smoke_clip.py data/smoke/result.json /absolute/path/to/source.mp4`

Expected: ffprobe 显示输出时长与期望差异小于 1 秒；人工观看未明显切断语句。

- [ ] **Step 3：记录 Day 1 go/no-go**

`docs/day1-validation.md` 填写样例时长、处理耗时、usage、成本、时间点偏差、是否启用 ASR。若切点明显不稳，下一步只在两者中选择一个：增大缓冲到 1.5 秒；或加入本地 faster-whisper。不得同时扩展 UI 和 ASR。

- [ ] **Step 4：提交验证资产**

```bash
git add scripts docs/day1-validation.md
git commit -m "test: validate end-to-end analysis and clipping"
```

---

## Task 8：实现安全的 FFmpeg Remix 服务

**Files:**
- Create: `apps/api/app/services/remix.py`
- Create: `apps/api/app/routes/remixes.py`
- Create: `apps/api/tests/test_remix.py`
- Modify: `apps/api/app/main.py`

- [ ] **Step 1：写失败测试**

覆盖：只接受当前视频 analysis 中的 insight ID；保留用户排序；1–8 个片段；合计不超过 180 秒；拒绝前端路径和任意时间戳；FFmpeg 命令无 shell；输出存在且可被 ffprobe 读取；失败可单独重试。

- [ ] **Step 2：实现 Remix 请求合同**

```python
class RemixCreate(BaseModel):
    insight_ids: list[str] = Field(min_length=1, max_length=8)

class RemixRead(BaseModel):
    id: str
    status: Literal["queued", "rendering", "completed", "failed"]
    duration_ms: int | None
    download_url: str | None
    error_code: str | None
```

- [ ] **Step 3：实现确定性渲染**

从数据库解析可信时间段；每段统一 `libx264/yuv420p/aac/48kHz`；使用 concat demuxer 拼接；输出 `-movflags +faststart`。所有中间文件位于 `data/tmp/{remix_id}`，成功或失败后清理；源文件和完成输出保留。

- [ ] **Step 4：实现端点**

```text
POST /api/videos/{video_id}/remixes
GET  /api/remixes/{remix_id}
POST /api/remixes/{remix_id}/retry
GET  /api/remixes/{remix_id}/download
```

创建返回 202；下载使用数据库中的 output key；Content-Disposition 使用安全文件名。

- [ ] **Step 5：运行媒体测试并提交**

Run: `cd apps/api && uv run pytest tests/test_remix.py -q`

Expected: PASS，生成文件有视频和音频流。

```bash
git add apps/api/app/services/remix.py apps/api/app/routes/remixes.py apps/api/app/main.py apps/api/tests/test_remix.py
git commit -m "feat: render ordered insight remixes with ffmpeg"
```

---

## Task 9：实现上传页和真实进度体验

**Files:**
- Create: `apps/web/src/lib/api.ts`
- Create: `apps/web/src/lib/format.ts`
- Create: `apps/web/src/components/UploadPanel.tsx`
- Create: `apps/web/src/components/JobProgress.tsx`
- Modify: `apps/web/src/app/page.tsx`
- Create: `apps/web/tests/UploadPanel.test.tsx`
- Create: `apps/web/tests/JobProgress.test.tsx`

- [ ] **Step 1：写组件失败测试**

覆盖：只接受 mp4/mov/webm；展示 300 MB、3–15 分钟限制；超限不发请求；上传成功跳转 `/jobs/{jobId}`；状态映射真实阶段；failed 显示用户文案和重试按钮，不展示堆栈。

- [ ] **Step 2：实现类型化 API client**

`api.ts` 提供 `uploadVideo`、`getJob`、`getResult`、`retryJob`、`createRemix`、`getRemix`。非 2xx 统一解析 `{code,message}` 为 `ApiError`；polling 使用 2 秒间隔、页面卸载时取消。

- [ ] **Step 3：实现上传首页**

首页包含一句价值主张、拖拽区、约束提示和样例入口。浏览器预检只改善体验，服务端仍是最终校验者。上传时显示真实传输状态，不伪造模型百分比。

- [ ] **Step 4：实现阶段进度**

阶段文案固定为：上传完成、视频预处理、理解视频内容、生成教学洞察、分析完成。未知/失败状态有明确兜底。完成后停止轮询并请求 result。

- [ ] **Step 5：验证并提交**

Run: `pnpm --dir apps/web test && pnpm --dir apps/web lint`

Expected: PASS。

```bash
git add apps/web/src apps/web/tests
git commit -m "feat: add video upload and analysis progress UI"
```

---

## Task 10：实现分析工作台、播放器联动和 Remix 选择

**Files:**
- Create: `apps/web/src/components/VideoWorkspace.tsx`
- Create: `apps/web/src/components/InsightCard.tsx`
- Create: `apps/web/src/components/RemixTray.tsx`
- Create: `apps/web/src/app/jobs/[jobId]/page.tsx`
- Create: `apps/web/tests/VideoWorkspace.test.tsx`
- Create: `apps/web/tests/RemixTray.test.tsx`

- [ ] **Step 1：写交互失败测试**

覆盖：显示摘要/章节/观点/证据/置信度；点击时间跳转 video.currentTime；选择/取消观点；上移/下移排序；总时长计算；超过 180 秒禁用生成；生成后轮询并显示预览与下载。

- [ ] **Step 2：实现播放器工作台**

桌面端左侧 sticky 视频、右侧洞察；移动端垂直布局。时间戳使用 `formatDuration(ms)`，点击设置 `video.currentTime = ms / 1000` 并播放。视觉证据与转写证据分别标识。

- [ ] **Step 3：实现 RemixTray**

只提交 insight IDs 和顺序，不提交路径或时间戳。使用原生按钮完成上下移动，避免三天 MVP 引入拖拽库；显示片段数、预计时长、边界缓冲说明和删除按钮。

- [ ] **Step 4：实现刷新恢复与状态空态**

路由直接以 jobId 查询数据库状态。处理 loading、processing、completed、failed、404 五种状态；completed 结果不可解析时显示 `RESULT_UNAVAILABLE`，不渲染半成品。

- [ ] **Step 5：验证并提交**

Run: `pnpm --dir apps/web test && pnpm --dir apps/web lint`

Expected: PASS。

```bash
git add apps/web/src apps/web/tests
git commit -m "feat: add evidence workspace and remix composer"
```

---

## Task 11：端到端测试、异常与演示兜底

**Files:**
- Create: `apps/web/tests/happy-path.spec.ts`
- Create: `apps/web/tests/error-paths.spec.ts`
- Create: `samples/demo-result.json`
- Create: `samples/README.md`
- Modify: `Makefile`

- [ ] **Step 1：创建稳定的 API mock/fixture**

`demo-result.json` 必须通过后端 `AnalysisPayload` 校验，包含至少 3 个章节和 4 个观点，时间范围均位于配套演示视频内。记录素材 URL、作者、许可和下载日期；不能把无权再分发的视频提交到仓库。

- [ ] **Step 2：写 Playwright happy path**

流程：打开首页 → 上传 fixture → 看到阶段变化 → 查看结果 → 点击时间戳 → 选择两个观点 → 调整顺序 → 生成 Remix → 播放器可加载 → 下载链接返回 MP4。

- [ ] **Step 3：写关键错误路径**

覆盖：错误格式、超大文件、模型 401、模型超时、非法模型 JSON、FFmpeg 失败、刷新恢复。断言用户看到下一步行动，不出现 API Key、Base URL、Python traceback 或本地绝对路径。

- [ ] **Step 4：增加一键全量验证**

Makefile 的 `verify` 顺序运行：后端单元测试、前端测试、lint、typecheck、Playwright；live 模型测试单列为 `test-live`，避免每次验证产生费用。

- [ ] **Step 5：运行并提交**

Run: `make verify`

Expected: 所有离线测试 PASS；无真实 API 消费。

```bash
git add apps/web/tests samples Makefile
git commit -m "test: cover happy path and critical failures"
```

---

## Task 12：真实样例评测与产品化收尾

**Files:**
- Create: `docs/evaluation.md`
- Create: `README.md`
- Modify: `docs/model-availability-audit.md`
- Modify: `docs/superpowers/specs/2026-09-17-ai-video-insight-remix-design.md`

- [ ] **Step 1：准备 3–5 个评测样例**

至少覆盖：真人讲解+PPT、屏幕录制/代码演示、低音质或视觉信息主导。每条 3–15 分钟且来源可说明。不要只用模型最擅长的一个样例。

- [ ] **Step 2：执行评测并记录量化结果**

`evaluation.md` 每条记录：时长、总处理时间、摘要可用性、章节边界误差、观点证据是否可定位、裁剪首尾是否完整、成功率、模型 usage、估算成本、人工备注。指标口径：

```text
章节边界可接受：人工判断误差 <= 10 秒
观点证据可定位：点击后 5 秒内能听到/看到支撑内容
Remix 完整：无明显断句，音视频正常，顺序正确
演示成功率：同一样例连续 3 次至少成功 2 次
```

- [ ] **Step 3：只修复最高影响 badcase**

按 `主链路阻断 > 错误切点 > 结果不可理解 > 视觉细节` 排序。若时间戳问题超过 1/3 样例，再引入本地 `faster-whisper`；否则保留“VL + 1–1.5 秒缓冲 + 人工确认”，不扩大技术栈。

- [ ] **Step 4：完成 README**

必须包含：产品截图/GIF、用户问题、3 分钟演示流程、架构图、模型选择、`.env.example`、本地安装/启动、测试命令、支持边界、成本实测、隐私说明、已知限制、Roadmap。明确“部署暂不在本次范围”。

- [ ] **Step 5：最终安全和质量验证**

Run:

```bash
make verify
rg -n "API_KEY=.+|ON_DEMAND_API_KEY=.+|sk-[A-Za-z0-9]" . --glob '!.env' --glob '!node_modules/**' --glob '!.next/**'
git status --short
```

Expected: 测试全部 PASS；凭据扫描无命中；只有计划内文件变更。

- [ ] **Step 6：录制演示并打版本标签**

录制 60–90 秒离线兜底视频，内容覆盖上传、洞察跳转、选择排序、Remix 播放。视频可放本地不提交大文件。最后提交：

```bash
git add README.md docs samples .env.example
git commit -m "docs: finalize evaluation and homework handoff"
git tag mvp-homework-v1
```

---

## 可选 Task 13：仅在评测证明必要时增加本地时间轴 ASR

**触发条件：** 3–5 个评测样例中，超过 1/3 的观点切点出现明显断句，且调整到 1.5 秒缓冲仍无法接受。

**Files:**
- Create: `apps/api/app/services/transcript.py`
- Create: `apps/api/tests/test_transcript.py`
- Modify: `apps/api/app/services/analysis.py`
- Modify: `apps/api/app/services/validator.py`

- [ ] **Step 1：写 segment 对齐失败测试**

给定 Qwen 候选范围和带时间戳的 Whisper segments，断言开始点吸附到相邻 segment.start，结束点吸附到 segment.end，且不超过视频范围。

- [ ] **Step 2：封装本地 faster-whisper adapter**

使用 `small` 模型、中文、VAD；返回 `[{start_ms,end_ms,text}]`。Adapter 可通过配置关闭；下载模型失败时降级回 VL 时间范围，不让主任务失败。

- [ ] **Step 3：加入分析状态与对齐**

只有 `ENABLE_LOCAL_ASR=true` 才运行；保存转写 JSON；洞察文本仍由 Qwen 生成，但时间边界对齐到最近的 segment。

- [ ] **Step 4：复跑同一评测集**

只有切点完整率显著改善且处理时长可接受才保留；否则移除该增强，避免为 Homework 增加无收益复杂度。

---

## 三天执行排程

| 时间 | 任务 | 硬产出 |
|---|---|---|
| Day 1 上午 | Task 1–3 | 项目可启动、数据合同、视频上传与 ffprobe |
| Day 1 下午 | Task 4–6 | 真实 Qwen 分析、状态机、结果持久化 |
| Day 1 晚上 | Task 7 | 一个真实视频得到洞察并裁出正确片段 |
| Day 2 上午 | Task 8–9 | Remix API、上传与进度 UI |
| Day 2 下午/晚上 | Task 10–11 | 完整工作台、排序、生成、下载、E2E |
| Day 3 上午 | Task 12 评测 | 3–5 个样例和 badcase 排序 |
| Day 3 下午 | P0 修复 | 主链路稳定、演示兜底 |
| Day 3 晚上 | README/录屏 | 可交付仓库、演示视频、版本标签 |

## 最终 Definition of Done

- `make verify` 全绿；
- 从全新浏览器进入首页能完成 P0 全流程；
- 真实模型调用和演示样例两条路径都可用，且明确标识；
- 任一失败状态都有可理解文案和恢复动作；
- Remix 输出能在 Chrome/Safari 播放并下载；
- 3–5 个样例评测、真实耗时、usage 和成本已记录；
- 仓库不含密钥、实际 Base URL、用户视频或未经授权素材；
- README 能让评审在 10 分钟内启动并理解产品取舍。
