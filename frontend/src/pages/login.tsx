"use client";
import { useState } from "react";
import { useAuth } from "../components/AuthProvider";
import { api } from "../utils/api";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const { setToken } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const router = useRouter();

  async function onLogin(e: React.FormEvent) {
    e.preventDefault();
    try {
      const res = await api.post("/auth/token", { username, password });
      setToken(res.data.token);
      router.push("/");
    } catch {
      alert("Login failed");
    }
  }
  return (
    <form onSubmit={onLogin} style={{ maxWidth: 400, margin: "100px auto" }}>
      <h1>Login</h1>
      <input
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        placeholder="Username"
      />
      <input
        value={password}
        type="password"
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Password"
      />
      <button type="submit">Login</button>
    </form>
  );
}
