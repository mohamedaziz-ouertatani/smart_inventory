"use client";
import { RequireAuth } from "../../components/RequireAuth";

export default function MetabaseDashboardPage() {
  const dashboardUrl =
    process.env.NEXT_PUBLIC_METABASE_DASHBOARD_URL ||
    "http://localhost:3001/public/dashboard/abcd1234-5678-etc"; // fallback

  return (
    <RequireAuth>
      <div style={{ width: "100%", minHeight: "900px" }}>
        <h1>Analytics Dashboard</h1>
        <iframe
          src={dashboardUrl}
          title="Metabase Analytics"
          style={{
            border: "none",
            width: "100%",
            height: "900px",
            marginTop: "24px",
            background: "white",
          }}
          allowFullScreen
        />
      </div>
    </RequireAuth>
  );
}
