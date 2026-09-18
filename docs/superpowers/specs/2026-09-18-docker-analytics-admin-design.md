# Docker 部署与埋点看板设计

## 目标

将 Framewise 部署到 Ubuntu 家庭小主机 Docker，支持局域网与 Tailscale 访问，并提供需要管理员登录的数据看板。

## 访问与部署

- 主机目录：`/home/klay/docker/stacks/framewise`；
- Web 入口：端口 3015，局域网 `192.168.3.16:3015`，Tailscale `100.73.108.79:3015`；
- API 与 Web 使用 Docker Compose，API 内置 FFmpeg；
- SQLite、上传视频、Remix、备份均使用持久化 bind mount；
- 不配置路由器端口转发，不暴露公网；
- 百炼 Key 只通过部署机 `.env` 注入。

## 埋点与看板

后端新增 `AnalyticsEvent` 表，事件采用固定名称、JSON properties、时间戳和匿名 session 标识。服务端事件优先，前端交互事件通过 API 上报；不存视频内容、模型 Key、管理员密码或完整文件名。

看板路由：`/admin/login`、`/admin/dashboard`。管理员密码使用 PBKDF2 哈希，会话使用 HttpOnly、SameSite Cookie；统计 API 仅允许有效会话访问。首个账号由部署脚本生成随机用户名和密码并写入未跟踪的部署 `.env`。

首版指标包括任务量、完成率、失败阶段/原因、分析耗时、模型 tokens/估算成本、观点选择率、Remix 成功率和下载次数。

## 验收

- `docker compose config` 成功；
- 容器健康检查通过；
- LAN 与 Tailscale 地址可打开 Web；
- 未登录访问 Dashboard 被重定向；登录后可查看聚合指标；
- 上传/分析/Remix 关键路径生成事件；
- SQLite 和媒体目录重启后数据保留；
- 账号密码、API Key 不进入 Git。
