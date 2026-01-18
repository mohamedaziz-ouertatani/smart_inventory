"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const fastify_plugin_1 = __importDefault(require("fastify-plugin"));
const pg_1 = require("pg");
const env_js_1 = require("../env.js");
async function ping(pool, attempts = 20, delayMs = 1000) {
    let lastErr;
    for (let i = 0; i < attempts; i++) {
        try {
            await pool.query("SELECT 1");
            return;
        }
        catch (err) {
            lastErr = err;
            await new Promise((res) => setTimeout(res, delayMs));
        }
    }
    throw lastErr ?? new Error("Database connectivity check failed");
}
exports.default = (0, fastify_plugin_1.default)(async (fastify) => {
    const pool = new pg_1.Pool({
        host: env_js_1.config.pg.host,
        port: env_js_1.config.pg.port,
        database: env_js_1.config.pg.database,
        user: env_js_1.config.pg.user,
        password: env_js_1.config.pg.password,
        ssl: env_js_1.config.pg.ssl,
    });
    try {
        await ping(pool, 20, 1000);
        fastify.log.info("Connected to PostgreSQL");
    }
    catch (err) {
        fastify.log.error({ err }, "Failed to connect to PostgreSQL");
        throw err;
    }
    fastify.decorate("db", pool);
    fastify.addHook("onClose", async () => {
        await pool.end();
    });
});
