"use client";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface Forecast {
  sku_id: string;
  location_id: string;
  horizon_week_start: string;
  forecast_units: string;
  model_name: string;
}

export default function ForecastChart({ data }: { data: Forecast[] }) {
  // Transform data: group by model_name
  const chartData = data.map((f) => ({
    model: f.model_name,
    forecast: Number(f.forecast_units),
    sku: f.sku_id,
  }));

  return (
    <ResponsiveContainer width="100%" height={400}>
      <BarChart data={chartData}>
        <XAxis dataKey="model" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Bar dataKey="forecast" fill="#8884d8" />
      </BarChart>
    </ResponsiveContainer>
  );
}
