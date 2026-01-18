"use client";
import { useEffect, useState } from "react";
import { api } from "../utils/api";
import { useAuth } from "../components/AuthProvider";
import ForecastChart from "@/components/ForecastChart";

interface Forecast {
  sku_id: string;
  location_id: string;
  horizon_week_start: string;
  forecast_units: string;
  model_name: string;
}

export default function ForecastPage() {
  const [forecasts, setForecasts] = useState<Forecast[]>([]);
  const { token } = useAuth();

  useEffect(() => {
    if (!token) return;
    api
      .get("/forecasts?latest_only=true&limit=20", {
        headers: { Authorization: `Bearer ${token}` },
      })
      .then((res) => setForecasts(res.data.data || res.data || []))
      .catch(() => setForecasts([]));
  }, [token]);

  if (!token) return <div>Please log in.</div>;
  return (
    <div>
      <h1>Latest Forecasts</h1>
      <ForecastChart data={forecasts} /> {/* ✅ Chart here */}
      <table>
        <thead>
          <tr>
            <th>SKU</th>
            <th>Location</th>
            <th>Start</th>
            <th>Forecast</th>
            <th>Model</th>
          </tr>
        </thead>
        <tbody>
          {forecasts.map((f) => (
            <tr key={f.sku_id + f.location_id + f.horizon_week_start}>
              <td>{f.sku_id}</td>
              <td>{f.location_id}</td>
              <td>{f.horizon_week_start}</td>
              <td>{f.forecast_units}</td>
              <td>{f.model_name}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
