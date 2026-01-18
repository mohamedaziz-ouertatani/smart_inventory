import { RequireAuth } from "../../components/RequireAuth";

export default function ForecastsPage() {
  return (
    <RequireAuth>
      {/* Your Forecasts UI here */}
      <h1>Forecasts (Protected)</h1>
      {/* ... */}
    </RequireAuth>
  );
}
