"use client";
import Link from "next/link";
import { useAuth } from "./AuthProvider";
import LogoutButton from "./LogoutButton";

export default function NavBar() {
  const { token } = useAuth();

  return (
    <nav style={{ display: "flex", gap: 20, padding: 12 }}>
      <Link href="/">Home</Link>
      {token && <Link href="/forecasts">Forecasts</Link>}
      {token && <Link href="/metabase-dashboard">Dashboards</Link>}
      {!token ? <Link href="/login">Login</Link> : <LogoutButton />}
    </nav>
  );
}
