"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.registerForecastRoutes = registerForecastRoutes;
function toBool(v, def = true) {
    if (v === undefined || v === null)
        return def;
    if (typeof v === "boolean")
        return v;
    const s = String(v).toLowerCase();
    return ["1", "true", "yes", "y"].includes(s)
        ? true
        : ["0", "false", "no", "n"].includes(s)
            ? false
            : def;
}
async function registerForecastRoutes(app) {
    app.get("/forecasts", {
        preHandler: app.requireRoles(["viewer", "operator"]),
        schema: {
            querystring: {
                type: "object",
                properties: {
                    sku_id: { type: "string" },
                    location_id: { type: "string" },
                    start_week: { type: "string" },
                    end_week: { type: "string" },
                    run_id: { type: "string" },
                    latest_only: { type: "boolean", default: true },
                    model_name: { type: "string" },
                    model_stage: {
                        type: "string",
                        enum: ["Production", "Staging", "None"],
                        default: "Production",
                    },
                    limit: { type: "integer", minimum: 1, maximum: 1000, default: 100 },
                    offset: { type: "integer", minimum: 0, default: 0 },
                },
                additionalProperties: false,
            },
        },
    }, async (req) => {
        const { sku_id, location_id, start_week, end_week, run_id, model_name, model_stage = "Production", limit = 100, offset = 0, } = req.query;
        const latestOnly = toBool(req.query.latest_only, true);
        let effectiveRunId = run_id;
        if (!effectiveRunId && latestOnly) {
            const runRes = await req.server.db.query(`SELECT run_id
         FROM ops.batch_run
         WHERE job_type = 'batch_inference' AND status = 'succeeded'
         ORDER BY started_at DESC
         LIMIT 1`);
            if (runRes.rowCount && runRes.rows[0]) {
                effectiveRunId = runRes.rows[0].run_id;
            }
        }
        const clauses = [];
        const params = [];
        let p = 1;
        if (effectiveRunId) {
            clauses.push(`f.run_id = $${p++}`);
            params.push(effectiveRunId);
        }
        if (sku_id) {
            clauses.push(`f.sku_id = $${p++}`);
            params.push(sku_id);
        }
        if (location_id) {
            clauses.push(`f.location_id = $${p++}`);
            params.push(location_id);
        }
        if (start_week) {
            clauses.push(`f.horizon_week_start >= $${p++}`);
            params.push(start_week);
        }
        if (end_week) {
            clauses.push(`f.horizon_week_start <= $${p++}`);
            params.push(end_week);
        }
        if (model_name) {
            clauses.push(`f.model_name = $${p++}`);
            params.push(model_name);
        }
        if (model_stage) {
            clauses.push(`f.model_stage = $${p++}`);
            params.push(model_stage);
        }
        const whereSql = clauses.length ? `WHERE ${clauses.join(" AND ")}` : "";
        params.push(limit, offset);
        const sql = `
      SELECT
        f.sku_id,
        f.location_id,
        f.horizon_week_start::text,
        f.forecast_units::text,
        f.baseline_units::text,
        f.residual_std::text,
        f.model_name,
        f.model_stage,
        f.generated_at::timestamptz::text
      FROM ops.forecast f
      ${whereSql}
      ORDER BY f.horizon_week_start DESC, f.sku_id, f.location_id
      LIMIT $${p++} OFFSET $${p++}
    `;
        const { rows } = await req.server.db.query(sql, params);
        return {
            meta: {
                run_id: effectiveRunId ?? null,
                latest_only: latestOnly,
                model_stage,
            },
            data: rows,
        };
    });
}
