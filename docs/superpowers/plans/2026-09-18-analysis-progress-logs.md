# 视频理解进度日志 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在分析任务页持久化并展示视频理解的片段进度、当前动作、耗时提示与最近 20 条用户友好日志。

**Architecture:** 使用 `AnalysisJob` 保存可快速轮询的进度快照，使用独立 `AnalysisJobLog` 表保存追加式历史。分析服务在切片、模型调用、完成、重试及失败节点写入进度；现有 Job API 聚合快照和最近日志，前端继续两秒轮询并在“理解视频内容”节点内渲染。

**Tech Stack:** FastAPI、SQLModel、SQLite、pytest、Next.js 16、React 19、TypeScript、Vitest、Testing Library。

---

## 文件结构

- Modify `apps/api/app/models.py`：新增 Job 进度字段和 `AnalysisJobLog`。
- Modify `apps/api/app/db.py`：为已有 SQLite 数据库执行幂等轻量迁移。
- Modify `apps/api/app/schemas.py`：定义日志响应及扩展 Job 响应。
- Create `apps/api/app/services/job_progress.py`：集中计算、持久化进度和脱敏日志。
- Modify `apps/api/app/services/analysis.py`：在长视频片段生命周期调用进度服务。
- Modify `apps/api/app/services/bailian.py`：通过可选回调报告模型重试。
- Modify `apps/api/app/routes/jobs.py`：返回最近 20 条日志，重试时重置进度并追加分隔日志。
- Modify `apps/api/tests/test_analysis.py`、`test_bailian.py`、`test_models.py`：后端行为与序列化测试。
- Modify `apps/web/src/lib/types.ts`：同步 Job 进度与日志类型。
- Modify `apps/web/src/components/JobProgress.tsx`：渲染进度详情与日志。
- Modify `apps/web/src/app/jobs/[jobId]/page.tsx`：将完整 Job 传入组件。
- Modify `apps/web/src/app/globals.css`：进度条和日志面板样式。
- Modify `apps/web/tests/JobProgress.test.tsx`：前端状态测试。

### Task 1: 持久化数据模型与兼容迁移

**Files:**
- Modify: `apps/api/app/models.py`
- Modify: `apps/api/app/db.py`
- Test: `apps/api/tests/test_models.py`

- [ ] **Step 1: 写入失败测试**

在 `test_models.py` 创建内存数据库，断言 `AnalysisJob` 默认进度为 `0/0/0`，并能持久化如下日志：

```python
log = AnalysisJobLog(job_id=job.id, stage="understanding", level="info", message="正在理解第 1/3 个片段")
session.add(log)
session.commit()
assert session.get(AnalysisJobLog, log.id).message == "正在理解第 1/3 个片段"
```

- [ ] **Step 2: 验证测试按预期失败**

Run: `cd apps/api && .venv/bin/pytest tests/test_models.py -q`
Expected: FAIL，提示 `AnalysisJobLog` 或进度字段不存在。

- [ ] **Step 3: 实现模型**

为 `AnalysisJob` 增加：

```python
progress_current: int = 0
progress_total: int = 0
progress_percent: int = 0
progress_message: str | None = None
```

新增：

```python
class AnalysisJobLog(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    job_id: str = Field(foreign_key="analysisjob.id", index=True)
    stage: str
    level: str = "info"
    message: str
    created_at: datetime = Field(default_factory=utc_now, index=True)
```

在 `init_db()` 的 `create_all()` 后，通过 SQLite `PRAGMA table_info(analysisjob)` 检查字段并逐条执行 `ALTER TABLE ... ADD COLUMN`。迁移必须幂等，默认值分别为 `0, 0, 0, NULL`。

- [ ] **Step 4: 运行模型测试**

Run: `cd apps/api && .venv/bin/pytest tests/test_models.py -q`
Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add apps/api/app/models.py apps/api/app/db.py apps/api/tests/test_models.py
git commit -m "feat: persist analysis job progress"
```

### Task 2: 建立进度日志领域服务

**Files:**
- Create: `apps/api/app/services/job_progress.py`
- Test: `apps/api/tests/test_analysis.py`

- [ ] **Step 1: 写入失败测试**

测试 `initialize_progress(session, job, 65_000, 30_000)` 得到总数 3；测试 `start_segment` 和 `complete_segment` 后快照、百分比与日志正确；批量写入 25 条后 `recent_logs(..., 20)` 只返回最新 20 条并保持时间升序。

- [ ] **Step 2: 验证测试按预期失败**

Run: `cd apps/api && .venv/bin/pytest tests/test_analysis.py -k progress -q`
Expected: FAIL，提示 `job_progress` 模块不存在。

- [ ] **Step 3: 实现最小领域 API**

实现以下明确接口：

```python
def append_job_log(session: Session, job: AnalysisJob, message: str, level: str = "info") -> AnalysisJobLog: ...
def initialize_progress(session: Session, job: AnalysisJob, duration_ms: int, segment_ms: int) -> None: ...
def set_progress_message(session: Session, job: AnalysisJob, message: str, level: str = "info") -> None: ...
def complete_segment(session: Session, job: AnalysisJob, segment_number: int) -> None: ...
def recent_logs(session: Session, job_id: str, limit: int = 20) -> list[AnalysisJobLog]: ...
```

百分比使用 `round(current / total * 100)` 并限制在 `0..100`。每个函数负责一次原子 commit；日志 level 只接受 `info/warning/error`。

- [ ] **Step 4: 运行测试**

Run: `cd apps/api && .venv/bin/pytest tests/test_analysis.py -k progress -q`
Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add apps/api/app/services/job_progress.py apps/api/tests/test_analysis.py
git commit -m "feat: add persisted job progress service"
```

### Task 3: 接入片段分析与模型重试事件

**Files:**
- Modify: `apps/api/app/services/analysis.py`
- Modify: `apps/api/app/services/bailian.py`
- Test: `apps/api/tests/test_analysis.py`
- Test: `apps/api/tests/test_bailian.py`

- [ ] **Step 1: 写入失败测试**

扩展长视频测试，断言 65 秒视频产生以下消息：

```text
准备分析视频，共 3 个片段
正在生成第 1/3 个分析片段
正在理解第 1/3 个片段（00:00–00:30）
第 1/3 个片段理解完成
```

在 Bailian 测试中模拟第一次超时、第二次成功，断言回调收到：

```python
("warning", "模型响应较慢，正在进行第 2 次尝试")
```

- [ ] **Step 2: 验证测试按预期失败**

Run: `cd apps/api && .venv/bin/pytest tests/test_analysis.py tests/test_bailian.py -q`
Expected: FAIL，缺少进度调用和 retry callback。

- [ ] **Step 3: 实现模型重试回调**

为 `BailianVideoAdapter.analyze` 与 `_post_with_retry` 增加可选异步回调：

```python
ProgressCallback = Callable[[str, str], Awaitable[None]]
async def analyze(self, video_url: str, duration_ms: int, on_progress: ProgressCallback | None = None) -> ModelAnalysisResult: ...
```

仅在实际准备重试时发送 warning；不包含 URL、状态响应体或密钥。

- [ ] **Step 4: 接入分析进度**

`analyze_in_segments` 接收数据库 session 与 job，初始化总片段数；每段转码前、模型调用前、成功后分别更新。格式化时间范围为 `MM:SS–MM:SS`。回调通过 `set_progress_message` 落库。任务完成时设置 `current=total`、`percent=100` 并写“视频内容理解完成”；异常分支写脱敏 error 日志。

- [ ] **Step 5: 运行相关测试**

Run: `cd apps/api && .venv/bin/pytest tests/test_analysis.py tests/test_bailian.py -q`
Expected: PASS。

- [ ] **Step 6: 提交**

```bash
git add apps/api/app/services/analysis.py apps/api/app/services/bailian.py apps/api/tests/test_analysis.py apps/api/tests/test_bailian.py
git commit -m "feat: record video understanding progress"
```

### Task 4: 扩展 Job API 与重试语义

**Files:**
- Modify: `apps/api/app/schemas.py`
- Modify: `apps/api/app/routes/jobs.py`
- Test: `apps/api/tests/test_analysis.py`

- [ ] **Step 1: 写入失败测试**

创建含 25 条日志的任务，断言 `GET /api/jobs/{id}` 返回四个进度字段及 20 条日志，日志由旧到新；调用 retry 后断言进度清零、旧日志保留且末条为“重新开始视频分析”。

- [ ] **Step 2: 验证测试按预期失败**

Run: `cd apps/api && .venv/bin/pytest tests/test_analysis.py -k "endpoint or retry" -q`
Expected: FAIL，响应缺少 progress/logs。

- [ ] **Step 3: 扩展 schema 和序列化**

新增：

```python
class AnalysisJobLogRead(BaseModel):
    id: str
    stage: str
    level: Literal["info", "warning", "error"]
    message: str
    created_at: datetime
```

`AnalysisJobRead` 增加四个进度字段和 `logs: list[AnalysisJobLogRead]`。`serialize_job` 接收 session 并调用 `recent_logs`。retry 清零快照、更新时间、写入分隔日志后再提交后台任务。

- [ ] **Step 4: 运行 API 测试**

Run: `cd apps/api && .venv/bin/pytest tests/test_analysis.py -q`
Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add apps/api/app/schemas.py apps/api/app/routes/jobs.py apps/api/tests/test_analysis.py
git commit -m "feat: expose analysis progress logs"
```

### Task 5: 展示用户友好的理解进度面板

**Files:**
- Modify: `apps/web/src/lib/types.ts`
- Modify: `apps/web/src/components/JobProgress.tsx`
- Modify: `apps/web/src/app/jobs/[jobId]/page.tsx`
- Modify: `apps/web/src/app/globals.css`
- Modify: `apps/web/tests/JobProgress.test.tsx`

- [ ] **Step 1: 写入失败组件测试**

构造 `understanding` Job（`progress_current=2`、`progress_total=15`、`progress_percent=13`），断言页面显示“第 3/15 个片段”、`13%`、当前消息和日志。再测试空日志显示“正在准备视频理解”，failed 状态同时保留日志和重试按钮。

- [ ] **Step 2: 验证测试按预期失败**

Run: `cd apps/web && npm test -- JobProgress.test.tsx --run`
Expected: FAIL，组件不接受 job/progress/logs。

- [ ] **Step 3: 扩展 TypeScript 类型**

定义 `AnalysisJobLog`，并为 `AnalysisJob` 增加与 API 一致的四个进度字段及 `logs: AnalysisJobLog[]`。

- [ ] **Step 4: 实现组件**

将组件签名调整为：

```tsx
export function JobProgress({ job, onRetry }: { job: AnalysisJob; onRetry?: () => void })
```

在 understanding 或 failed 且存在日志时渲染 `role="progressbar"`（包含 `aria-valuenow/min/max`）、片段计数、当前消息及 `<ol aria-label="分析日志">`。使用 `Intl.DateTimeFormat("zh-CN", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" })` 格式化时间。

- [ ] **Step 5: 更新页面和样式**

Job 页面传入完整 `job`。新增 `.understanding-progress`、`.progress-meter`、`.progress-fill`、`.job-log-list`、`.job-log-warning`、`.job-log-error`，日志容器设置合理最大高度与滚动，不改变现有整体布局。

- [ ] **Step 6: 运行前端测试**

Run: `cd apps/web && npm test -- JobProgress.test.tsx --run`
Expected: PASS。

- [ ] **Step 7: 提交**

```bash
git add apps/web/src/lib/types.ts apps/web/src/components/JobProgress.tsx 'apps/web/src/app/jobs/[jobId]/page.tsx' apps/web/src/app/globals.css apps/web/tests/JobProgress.test.tsx
git commit -m "feat: show video understanding progress logs"
```

### Task 6: 全量验证与本地页面验收

**Files:**
- Modify only if verification reveals a defect in files already listed above.

- [ ] **Step 1: 运行后端全量测试**

Run: `cd apps/api && .venv/bin/pytest -q`
Expected: 全部 PASS。

- [ ] **Step 2: 运行前端测试和构建**

Run: `cd apps/web && npm test -- --run && npm run build`
Expected: Vitest 全部 PASS，Next.js build 退出码 0。

- [ ] **Step 3: 本地 UI 验收**

启动本地服务，打开一个处于 understanding 的任务，确认两次轮询后进度与日志更新、刷新页面后日志保留、日志区域可滚动、移动端无横向溢出。只验证本地 `localhost`，不连接或部署远程服务器。

- [ ] **Step 4: 检查变更范围**

Run: `git status --short && git diff --check`
Expected: 无未预期文件，`git diff --check` 退出码 0。

- [ ] **Step 5: 提交验证阶段必要修复**

仅当本任务产生修复时执行：

```bash
git add apps/api apps/web
git commit -m "fix: finalize analysis progress experience"
```

## 非目标与部署约束

- 不引入 SSE、WebSocket、Redis 或外部队列。
- 不在页面暴露供应商、Base URL、请求体、响应体、密钥和堆栈。
- 不删除历史日志；API 只返回最近 20 条。
- 本计划完成后不部署 Lighthouse 或 Ubuntu，等待用户明确授权。
