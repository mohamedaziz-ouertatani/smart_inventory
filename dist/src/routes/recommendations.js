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
export async function registerRecommendationRoutes(app) {
    app.get("/recommendations", {
        preHandler: app.requireRoles(["viewer", "operator"]),
        schema: {
            querystring: {
                type: "object",
                properties: {
                    sku_id: { type: "string" },
                    location_id: { type: "string" },
                    start_week: { type: "string" }, // YYYY-MM-DD
                    end_week: { type: "string" },
                    run_id: { type: "string" }, // UUID
                    latest_only: { type: "boolean", default: true },
                    limit: { type: "integer", minimum: 1, maximum: 1000, default: 100 },
                    offset: { type: "integer", minimum: 0, default: 0 },
                },
                additionalProperties: false,
            },
        },
    }, async (req) => {
        const { sku_id, location_id, start_week, end_week, run_id, limit = 100, offset = 0, } = req.query;
        const latestOnly = toBool(req.query.latest_only, true);
        let effectiveRunId = run_id;
        if (!effectiveRunId && latestOnly) {
            const runRes = await req.server.db.query(`SELECT run_id
         FROM ops.batch_run
         WHERE job_type = 'compute_policy' AND status = 'succeeded'
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
            clauses.push(`r.run_id = $${p++}`);
            params.push(effectiveRunId);
        }
        if (sku_id) {
            clauses.push(`r.sku_id = $${p++}`);
            params.push(sku_id);
        }
        if (location_id) {
            clauses.push(`r.location_id = $${p++}`);
            params.push(location_id);
        }
        if (start_week) {
            clauses.push(`r.as_of_week_start >= $${p++}`);
            params.push(start_week);
        }
        if (end_week) {
            clauses.push(`r.as_of_week_start <= $${p++}`);
            params.push(end_week);
        }
        const whereSql = clauses.length ? `WHERE ${clauses.join(" AND ")}` : "";
        params.push(limit, offset);
        const sql = `
      SELECT
        r.sku_id,
        r.location_id,
        r.as_of_week_start::text,
        r.lead_time_weeks,
        r.service_level::text,
        r.rop_units::text,
        r.on_hand,
        r.on_order,
        r.order_qty,
        r.mu_lt::text,
        r.sigma_lt::text,
        r.z_value::text,
        r.computed_at::timestamptz::text
      FROM ops.replenishment_recommendation r
      ${whereSql}
      ORDER BY r.as_of_week_start DESC, r.sku_id, r.location_id
      LIMIT $${p++} OFFSET $${p++}
    `;
        const { rows } = await req.server.db.query(sql, params);
        return {
            meta: {
                run_id: effectiveRunId ?? null,
                latest_only: latestOnly,
            },
            data: rows,
        };
    });
}
