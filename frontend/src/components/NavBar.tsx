"use client";
import Link from "next/link";

export default function NavBar() {
  return (
    <nav style={{ padding: "1rem", borderBottom: "1px solid #ccc" }}>
      <Link href="/">Home</Link> | <Link href="/login">Login</Link> |{" "}
      <Link href="/forecasts">Forecasts</Link>
    </nav>
  );
}
