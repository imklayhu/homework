"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { API_BASE_URL } from "@/lib/api";

export default function AdminLogin() {
  const router = useRouter();
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const response = await fetch(`${API_BASE_URL}/api/admin/authenticate`, {
      method: "POST",
      credentials: "include",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ username: data.get("username"), password: data.get("password") }),
    });
    if (!response.ok) { setError("账号或密码错误"); return; }
    router.push("/admin/dashboard");
  }

  return <main className="home-shell"><section className="admin-login-panel">
    <div><p className="eyebrow">ADMIN / DEMO ACCESS</p><h1>管理员登录</h1><p className="admin-login-lede">查看这份作品的产品运行数据、任务效率和失败归因。</p></div>
    <form onSubmit={submit} className="upload-form"><label>账号<input name="username" placeholder="账号" required /></label><label>密码<input name="password" type="password" placeholder="密码" required /></label><button className="primary-button" type="submit">登录看板</button>{error && <p role="alert">{error}</p>}</form>
    <aside className="demo-credentials" aria-label="演示账号提示"><strong>演示环境</strong><span>演示账号：{process.env.NEXT_PUBLIC_DEMO_ADMIN_USERNAME ?? "admin"}</span><span>演示密码：{process.env.NEXT_PUBLIC_DEMO_ADMIN_PASSWORD ?? "请联系作品作者"}</span><small>仅用于查看面试作品数据，不包含模型密钥。</small></aside>
  </section></main>;
}
