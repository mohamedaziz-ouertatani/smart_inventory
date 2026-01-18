"use client";
import { useEffect, useState } from "react";
import { RequireAuth } from "../../components/RequireAuth"; // Path based on your structure

export default function MetabaseDashboardPage() {
  const [dashboardUrl, setDashboardUrl] = useState("");

  useEffect(() => {
    fetch("/api/metabase-embed-url")
      .then((res) => res.json())
      .then((data) => setDashboardUrl(data.url));
  }, []);

  return (
    <RequireAuth>
      <div style={{ width: "100%", minHeight: "900px" }}>
        <h1>Analytics Dashboard</h1>
        {dashboardUrl && (
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
        )}
      </div>
    </RequireAuth>
  );
}
