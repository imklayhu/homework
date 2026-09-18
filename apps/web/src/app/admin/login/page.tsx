"use client";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { API_BASE_URL } from "@/lib/api";
export default function AdminLogin() {
  const router = useRouter(); const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const data = new FormData(event.currentTarget); const response = await fetch(`${API_BASE_URL}/api/admin/login`, { method: "POST", credentials: "include", headers: { "content-type": "application/json" }, body: JSON.stringify({ username: data.get("username"), password: data.get("password") }) }); if (!response.ok) { setError("账号或密码错误"); return; } router.push("/admin/dashboard"); }
  return <main className="home-shell"><section className="upload-panel"><p className="eyebrow">ADMIN</p><h1>管理员登录</h1><form onSubmit={submit} className="upload-form"><input name="username" placeholder="账号" required /><input name="password" type="password" placeholder="密码" required /><button type="submit">登录</button>{error && <p role="alert">{error}</p>}</form></section></main>;
}
