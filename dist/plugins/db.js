"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const fastify_plugin_1 = __importDefault(require("fastify-plugin"));
const pg_1 = require("pg");
const env_js_1 = require("../env.js");
exports.default = (0, fastify_plugin_1.default)(async (fastify) => {
    const pool = new pg_1.Pool({
        host: env_js_1.config.pg.host,
        port: env_js_1.config.pg.port,
        database: env_js_1.config.pg.database,
        user: env_js_1.config.pg.user,
        password: env_js_1.config.pg.password,
        ssl: env_js_1.config.pg.ssl
    });
    // simple connectivity check on startup
    await pool.query('SELECT 1');
    fastify.decorate('db', pool);
    fastify.addHook('onClose', async () => {
        await pool.end();
    });
});
