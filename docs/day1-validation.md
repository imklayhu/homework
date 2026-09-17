# Day 1 技术风险验证

检查日期：2026-09-17

## 已验证结论

- ON_DEMAND `qwen3-vl-flash` 接受本地 MP4 的 Base64 data URL；
- 纯测试画面会诚实返回空结果，严格 Schema 会拒绝其进入产品；
- 仅使用 `json_object` 时，模型可能自行生成 `start_time/end_time` 等字段；
- 改为 OpenAI-compatible `json_schema` 且 `strict=true` 后，真实调用通过 Pydantic 合同；
- 66 秒中文教育讲解样例成功返回 1 个章节、1 个观点和候选时间范围；
- 本次调用耗时 11.19 秒，使用 39,206 video tokens、804 text input tokens、431 completion tokens，共 40,441 tokens；
- 按当前文档参考单价估算约 ¥0.033，实际价格以百炼账单为准；
- FFmpeg 能按模型结果裁出 H.264/AAC MP4，供后续播放器预览。

## 风险判断

该样例为 66 秒静态教学页，模型给出的候选范围覆盖完整视频，不能证明长视频的精细边界质量。下一步需要对 3–5 个 3–15 分钟、包含章节变化的样例评测。MVP 继续采用模型时间范围、1 秒边界缓冲和用户预览；只有超过三分之一样例明显断句时才增加本地 ASR。
