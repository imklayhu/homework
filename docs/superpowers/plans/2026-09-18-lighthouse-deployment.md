# Lighthouse Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the complete Framewise Web, API, FFmpeg preprocessing, and remix service on the existing Tencent Lighthouse host without disrupting FatTI, then move `wise.ai-dddd.top` from the home Tunnel to the Lighthouse origin.

**Architecture:** Keep the existing two-container Compose topology and bind Web only to Lighthouse loopback port 3015. Add a process-local capacity gate so the single API process executes at most one analysis or remix job at a time. Nginx terminates HTTPS for `wise.ai-dddd.top` and proxies to `127.0.0.1:3015`; FatTI remains on 8100/8101. Deploy through a dedicated SSH key installed with TAT, because interactive Lighthouse SSH requires QR login.

**Tech Stack:** FastAPI, asyncio, Next.js standalone, Docker Compose, FFmpeg, Nginx, Tencent TAT, Cloudflare DNS.

---

### Task 1: Add a single-job capacity gate

**Files:**
- Create: `apps/api/app/services/capacity.py`
- Modify: `apps/api/app/services/analysis.py`
- Modify: `apps/api/app/services/remix.py`
- Test: `apps/api/tests/test_capacity.py`

- [ ] **Step 1: Write a failing async test**

Create a test that starts two coroutines inside the shared capacity context. Hold the first coroutine on an event and assert the second has not entered; release the first and assert the second then enters.

- [ ] **Step 2: Verify the test fails**

Run `cd apps/api && uv run pytest tests/test_capacity.py -q`.

Expected: import failure because `app.services.capacity` does not exist.

- [ ] **Step 3: Implement the minimal gate**

Create one module-level `asyncio.Semaphore(1)` and expose it through an async context manager named `job_capacity`. Wrap the bodies of `execute_analysis_job` and the remix background executor with `async with job_capacity():` while leaving status persistence and error handling unchanged.

- [ ] **Step 4: Verify the focused and full API suites**

Run `cd apps/api && uv run pytest tests/test_capacity.py -q && uv run pytest -q`.

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/services/capacity.py apps/api/app/services/analysis.py apps/api/app/services/remix.py apps/api/tests/test_capacity.py
git commit -m "fix: serialize media processing jobs"
```

### Task 2: Constrain the Lighthouse containers

**Files:**
- Modify: `docker-compose.yml`
- Test: `docker-compose.yml`

- [ ] **Step 1: Add Lighthouse-safe runtime limits**

Bind Web with the existing `FRAMEWISE_BIND_IP` variable set to `127.0.0.1` on Lighthouse. Add `mem_limit: 768m` and `cpus: 1.75` to API; add `mem_limit: 384m` and `cpus: 0.50` to Web. Keep the API un-published and keep persistent `./data:/app/data` storage.

- [ ] **Step 2: Validate Compose locally**

Run `docker compose config >/dev/null`.

Expected: exit code 0.

- [ ] **Step 3: Run full local verification**

Run `cd apps/web && npm test -- --run && npm run build`, then `cd apps/api && uv run pytest -q`.

Expected: Web tests, Web production build, and API tests all pass.

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml
git commit -m "ops: constrain lighthouse containers"
```

### Task 3: Prepare Lighthouse deployment access and Docker

**Files:**
- Create locally: `~/.ssh/framewise_lighthouse` and `.pub`
- Create remotely: `/home/deploy/.ssh/authorized_keys`
- Create remotely: `/etc/docker/daemon.json`

- [ ] **Step 1: Create a dedicated Ed25519 deployment key**

Run `ssh-keygen -t ed25519 -N '' -C framewise-lighthouse -f ~/.ssh/framewise_lighthouse` only when the file does not already exist.

- [ ] **Step 2: Install only the public key through TAT**

Append the public key to `/home/deploy/.ssh/authorized_keys` only when absent. Set the directory to 700, file to 600, and ownership to `deploy:deploy`. Do not transmit or log the private key.

- [ ] **Step 3: Verify non-interactive SSH over Tailscale**

Run `ssh -i ~/.ssh/framewise_lighthouse -o BatchMode=yes deploy@100.117.61.102 'id -un'`.

Expected: `deploy`.

- [ ] **Step 4: Install Docker CE from a mainland mirror**

Through TAT, configure the Aliyun Docker CE CentOS repository, install Docker Engine and the Compose plugin, write registry mirrors to `/etc/docker/daemon.json`, enable Docker, and add `deploy` to the docker group.

- [ ] **Step 5: Verify Docker without changing FatTI**

Run `docker --version`, `docker compose version`, `systemctl is-active docker`, and re-check that `fatti-api-prod`, `fatti-api-dev`, PostgreSQL, and Nginx are active.

### Task 4: Upload and launch Framewise

**Files:**
- Create remotely: `/home/deploy/framewise/`
- Copy: repository files excluding `.git`, `data`, `node_modules`, `.next`, caches
- Copy securely: local `.env` to `/home/deploy/framewise/.env`

- [ ] **Step 1: Synchronize application files over SSH**

Use `rsync --delete` with explicit exclusions for `.git/`, `.env`, `data/`, `node_modules/`, `.next/`, `__pycache__/`, and `*.pyc`. Copy `.env` separately with `scp`, then set mode 600.

- [ ] **Step 2: Set Lighthouse-only environment overrides**

Append or replace `FRAMEWISE_BIND_IP=127.0.0.1`, `FRAMEWISE_PORT=3015`, and `CORS_ORIGIN=https://wise.ai-dddd.top` in the remote `.env` without printing any existing secret values.

- [ ] **Step 3: Build and start exactly two containers**

Run `docker compose up -d --build --remove-orphans` in `/home/deploy/framewise`.

- [ ] **Step 4: Verify the private origin**

Confirm Compose reports exactly `framewise-api-1` and `framewise-web-1`; API health is `ok`; `curl http://127.0.0.1:3015/` returns 200; ports 8100/8101 remain owned by FatTI.

### Task 5: Add and validate the Lighthouse Nginx site

**Files:**
- Create remotely: `/etc/nginx/conf.d/framewise.conf`

- [ ] **Step 1: Install an isolated virtual host**

Create HTTP redirect and HTTPS server blocks for `wise.ai-dddd.top`, reuse `/etc/nginx/ssl/ai-dddd.top.pem` and `.key`, set `client_max_body_size 320m`, disable request buffering for upload paths, and proxy all traffic to `http://127.0.0.1:3015` with long upload/read timeouts.

- [ ] **Step 2: Validate before reload**

Run `nginx -t` and stop if it fails. If valid, reload Nginx.

- [ ] **Step 3: Test the origin without changing DNS**

From Lighthouse, run `curl -k --resolve wise.ai-dddd.top:443:127.0.0.1 https://wise.ai-dddd.top/`. From the local machine, resolve the hostname to the Lighthouse public IP only for the request and confirm HTTPS 200.

- [ ] **Step 4: Re-verify FatTI**

Confirm both FatTI public health endpoints still return 200.

### Task 6: Cut over and run acceptance checks

**Files:**
- Update external state: Cloudflare DNS record for `wise.ai-dddd.top`
- Update: deployment notes in `docs/`

- [ ] **Step 1: Cut DNS only after origin acceptance**

Replace the Tunnel-target record with a proxied DNS record pointing to the Lighthouse public IP. If no scoped Cloudflare API credential exists locally, stop at this single manual dashboard action and provide the exact record change without exposing the IP in committed documentation.

- [ ] **Step 2: Verify public HTTPS**

Run `curl -fsS https://wise.ai-dddd.top/` and confirm HTTP 200. Confirm response reaches the Lighthouse Nginx access log.

- [ ] **Step 3: Upload a representative video**

Use the public Web UI to upload a video larger than 10 MiB. Confirm upload completes, exactly one analysis job runs, FFmpeg stays within the container limits, and the result page completes.

- [ ] **Step 4: Preserve rollback**

Do not remove the Ubuntu deployment during initial cutover. Rollback is the Cloudflare DNS/Tunnel record change back to the current home origin.

- [ ] **Step 5: Commit deployment documentation**

Record Lighthouse paths, services, verification evidence, rollback, and capacity limits without committing credentials or public IPs.
