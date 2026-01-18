// app/api/metabase-embed-url/route.js
import jwt from "jsonwebtoken";

// For security, store this key in your env and NOT in code in production!
const METABASE_SITE_URL = "http://localhost:3001";
const METABASE_SECRET_KEY = process.env.METABASE_SECRET_KEY;
const DASHBOARD_ID = 1; // CHANGE to your dashboard's numeric ID!

export async function GET(request) {
  const payload = {
    resource: { dashboard: DASHBOARD_ID },
    params: {},
    exp: Math.round(Date.now() / 1000) + 10 * 60, // 10 min expiry
  };

  const token = jwt.sign(payload, METABASE_SECRET_KEY);
  const url = `${METABASE_SITE_URL}/embed/dashboard/${token}#theme=light`;

  return new Response(JSON.stringify({ url }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}
