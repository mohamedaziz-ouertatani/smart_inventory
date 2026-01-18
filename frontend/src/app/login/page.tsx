"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "../../utils/api";
import { useAuth } from "../../components/AuthProvider";

export default function LoginPage() {
  const router = useRouter();
  const { setToken } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onLogin(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await api.post("/auth/token", { username, password });
      setToken(res.data.token);
      router.push("/"); // Redirect to home (or /forecasts if you like)
    } catch (err: any) {
      setToken(null);
      if (err.response && err.response.status === 401) {
        setError("Invalid username or password.");
      } else if (err.response) {
        setError(err.response.data?.message || "Server error.");
      } else {
        setError("Network/server error. Is your backend running?");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ maxWidth: 400, margin: "80px auto", padding: 20, border: "1px solid #eee", borderRadius: 12, background: "#fafbfc" }}>
      <h1 style={{ textAlign: "center" }}>Login</h1>
      <form onSubmit={onLogin}>
        <label>
          Username
          <input
            value={username}
            onChange={e => setUsername(e.target.value)}
            required
            autoFocus
            disabled={loading}
            style={{ width: "100%", marginBottom: 12, marginTop: 4 }}
          />
        </label>
        <label>
          Password
          <input
            value={password}
            onChange={e => setPassword(e.target.value)}
            type="password"
            required
            disabled={loading}
            style={{ width: "100%", marginBottom: 20, marginTop: 4 }}
          />
        </label>
        <button
          type="submit"
          disabled={loading}
          style={{
            width: "100%",
            background: "#1976d2",
            color: "#fff",
            border: "none",
            padding: "10px 0",
            borderRadius: 4,
            fontWeight: "bold",
            cursor: loading ? "not-allowed" : "pointer"
          }}
        >
          {loading ? "Logging in..." : "Login"}
        </button>
        {error && <div style={{ color: "red", marginTop: 16, textAlign: "center" }}>{error}</div>}
      </form>
    </div>
  );
}