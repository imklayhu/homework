# Lighthouse 视频中转可行性验证

日期：2026-09-18

## 结论

方案在功能上可行，适合把长时间传输从浏览器前台转移到后台，但当前网络条件下不能缩短视频进入分析前的总等待时间。

- 浏览器到 Lighthouse 明显快于浏览器经 Cloudflare Tunnel 直传家庭 Ubuntu。
- Lighthouse 到 Ubuntu 的 Tailscale 链路仍然较慢，是新方案的后台瓶颈。
- MVP 可以采用该方案改善用户上传体验，但产品必须明确展示“云端已接收，正在同步到分析节点”，不能在 Lighthouse 接收完成后宣称分析已开始。

## 已验证基础设施

- Lighthouse：腾讯云轻量服务器，CentOS 7。
- 远程运维：复用 `FatTI/devops/scripts/ops-remote.py` 的腾讯云 TAT `RunCommand` 模式。
- 公网入口：现有 Nginx、HTTPS 和 Cloudflare DNS/代理体系。
- 后台互联：Ubuntu 与 Lighthouse 均在线于 Tailscale；Ubuntu 可直连 Lighthouse 的 Tailscale 地址。
- 常驻服务：可复用 FatTI 的 systemd + Nginx 反向代理部署模式，使用独立服务、端口和域名，避免影响 FatTI 的 8100/8101 服务。

## 实测结果

### 浏览器侧到 Lighthouse

使用 FatTI 开发域名向不存在的探测路径发送请求，只测上传吞吐，不写入业务数据：

| 请求体 | 结果 | 用时 | 观测吞吐 |
| --- | --- | ---: | ---: |
| 1 MiB | HTTP 404（探测路径不存在，符合预期） | 4.25 秒 | 246,823 B/s，约 241 KiB/s |
| 8 MiB | HTTP 413 | 4.35 秒后拒绝 | 现有 Nginx 请求体上限不足 |

当前 Framewise 经 Cloudflare Tunnel 直传家庭 Ubuntu 约为 1 MiB/31–46 秒。因此第一段链路有明显改善空间。

### Lighthouse 到 Ubuntu

- `tailscale ping` 显示通过 Lighthouse 公网 UDP 地址直连，并非 DERP 中继。
- RTT 约 175 ms。
- 16 MiB 测试拉取在约 155 秒时只完成 3.8 MiB，约 25 KiB/s，随后主动终止测试。
- 该吞吐与现有 Cloudflare Tunnel 上传的量级接近。

按 25 KiB/s 粗略估算：

| 视频大小 | Lighthouse 到 Ubuntu 后台同步时间 |
| ---: | ---: |
| 100 MiB | 约 68 分钟 |
| 300 MiB | 约 3.4 小时 |

实际速度会随跨境网络波动。

## 推荐 MVP 架构

1. Ubuntu 创建上传会话，生成一次性 upload ID、短期令牌和 Lighthouse 上传地址。
2. 浏览器直接分片上传到 Lighthouse，不再让视频请求体经过家庭 Cloudflare Tunnel。
3. Lighthouse 保存临时文件并记录大小、SHA-256 和完成状态。
4. 浏览器完成上传后进入“云端已接收，正在同步到分析节点”状态。
5. Ubuntu 后台 worker 通过 Tailscale 主动拉取文件，支持流式写盘和失败重试。
6. Ubuntu 校验文件大小和 SHA-256，一致后注册视频并启动现有分析任务。
7. Ubuntu 调用 Lighthouse 删除接口；删除操作必须幂等。
8. Lighthouse 定时清理超时会话，避免 Ubuntu 未回调时遗留文件。

## 必要安全与运维约束

- 中转服务使用独立 systemd unit、独立端口、独立 Nginx server block 和独立临时目录。
- 公网上传接口必须使用一次性短期令牌，并限制文件大小、MIME、扩展名和每个 upload ID 的分片范围。
- 下载接口只监听 Tailscale 地址或只允许 Ubuntu 的 Tailscale IP，不允许公网匿名下载。
- Nginx 为中转服务单独配置至少 320 MiB 的请求体上限；不要修改 FatTI API 的全局限制。
- 文件落盘采用临时名和原子重命名；日志不得记录令牌、API Key 或完整下载 URL。
- Lighthouse 设置磁盘配额、会话 TTL 和定时清理。
- Ubuntu 仅在校验成功后删除远端文件；失败时保留到 TTL，便于自动重试。

## 成本与风险

- 浏览器上传到 Lighthouse 属于入站流量，通常不计 Lighthouse 公网出站流量。
- Lighthouse 向 Ubuntu 传输属于出站流量，可能消耗轻量服务器流量包；需按实际套餐确认额度和超额价格。
- 临时存储占用 Lighthouse 系统盘，峰值容量至少按“并发上传数 × 300 MiB”预留。
- 最大风险不是实现复杂度，而是 Lighthouse 到 Ubuntu 的低吞吐和跨境波动。

## 建议决策

若目标是“让用户更快离开上传页面”，可以进入 MVP 设计与实施；若目标是“更快开始 AI 分析”，当前 Lighthouse 中转方案不满足目标，应优先考虑同地域对象存储、把分析服务迁移到云端，或改善家庭服务器公网链路。

## 清理确认

验证使用的 Lighthouse 临时服务、临时防火墙端口、systemd unit 和测试文件均已删除；Ubuntu 临时下载文件也已删除。
