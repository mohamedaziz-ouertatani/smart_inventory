"use client";

import Link from "next/link";

export default function HomePage() {
  return (
    <main style={{ padding: "2rem", fontFamily: "sans-serif" }}>
      <h1>Welcome to Smart Inventory Analytics</h1>
      <p>Track your weekly performance and dive into interactive dashboards:</p>
      <nav style={{ marginTop: "2rem" }}>
        <ul style={{ listStyle: "none", padding: 0, fontSize: "1.2rem" }}>
          <li style={{ marginBottom: "1rem" }}>
            <Link href="/metabase-dashboard">
              <strong>Analytics Dashboard</strong>
            </Link>
          </li>
          <li style={{ marginBottom: "0.5rem" }}>
            <Link href="/weekly-demand">Weekly Demand</Link>
          </li>
          <li style={{ marginBottom: "0.5rem" }}>
            <Link href="/weekly-features">Weekly Features</Link>
          </li>
          <li style={{ marginBottom: "0.5rem" }}>
            <Link href="/weekly-inventory">Weekly Inventory</Link>
          </li>
        </ul>
      </nav>
      <hr style={{ margin: "2.5rem 0" }} />
      <section>
        <p>
          Use these dashboards and reports to track sales, inventory, and new
          product features every week, powered by your Metabase analytics.
        </p>
      </section>
    </main>
  );
}
