"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const fastify_1 = __importDefault(require("fastify"));
const env_js_1 = require("./env.js");
const db_js_1 = __importDefault(require("./plugins/db.js"));
const auth_js_1 = __importDefault(require("./plugins/auth.js"));
const health_js_1 = require("./routes/health.js");
const auth_js_2 = require("./routes/auth.js");
const forecasts_js_1 = require("./routes/forecasts.js");
const recommendations_js_1 = require("./routes/recommendations.js");
async function buildServer() {
    const app = (0, fastify_1.default)({
        logger: {
            level: env_js_1.config.nodeEnv === "development" ? "debug" : "info",
        },
    });
    await app.register(db_js_1.default);
    await app.register(auth_js_1.default);
    // Public route
    await (0, health_js_1.registerHealthRoutes)(app);
    // Auth routes (token issuance, whoami)
    await (0, auth_js_2.registerAuthRoutes)(app);
    // Protected routes
    await (0, forecasts_js_1.registerForecastRoutes)(app);
    await (0, recommendations_js_1.registerRecommendationRoutes)(app);
    return app;
}
const start = async () => {
    const app = await buildServer();
    try {
        await app.listen({ port: env_js_1.config.port, host: env_js_1.config.host });
        app.log.info(`Server listening on http://${env_js_1.config.host}:${env_js_1.config.port}`);
    }
    catch (err) {
        app.log.error(err);
        process.exit(1);
    }
};
start();
