export default function DashboardPage() {
  return (
    <div style={{ height: "90vh" }}>
      <iframe
        title="Metabase Dashboard"
        src="http://localhost:3001/public/dashboard/xxxxxxx-xxxx/"
        width="100%"
        height="100%"
        frameBorder={0}
      />
    </div>
  );
}
