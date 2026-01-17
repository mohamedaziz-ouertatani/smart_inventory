"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const fastify_1 = __importDefault(require("fastify"));
const dotenv_1 = __importDefault(require("dotenv"));
const env_js_1 = require("./env.js");
const db_js_1 = __importDefault(require("./plugins/db.js"));
const auth_js_1 = __importDefault(require("./plugins/auth.js"));
const auth_js_2 = require("./routes/auth.js");
const forecasts_js_1 = require("./routes/forecasts.js");
const recommendations_js_1 = require("./routes/recommendations.js");
dotenv_1.default.config();
async function buildServer() {
    const app = (0, fastify_1.default)({
        logger: {
            level: env_js_1.config.nodeEnv === "development" ? "debug" : "info",
        },
    });
    // Register plugins
    await app.register(db_js_1.default);
    await app.register(auth_js_1.default);
    // Built-in health route
    app.get("/health", async (_req, reply) => {
        app.log.info("Health check called");
        reply.send({
            status: "ok",
            time: new Date().toISOString(),
        });
    });
    // Auth routes (token issuance, whoami)
    await (0, auth_js_2.registerAuthRoutes)(app);
    // Protected routes
    await (0, forecasts_js_1.registerForecastRoutes)(app);
    await (0, recommendations_js_1.registerRecommendationRoutes)(app);
    // Print all registered routes to logs
    console.log(app.printRoutes());
    return app;
}
const start = async () => {
    const app = await buildServer();
    const port = env_js_1.config.port || 3000;
    const host = env_js_1.config.host || "0.0.0.0";
    try {
        await app.listen({ port, host });
        app.log.info(`Server listening on http://${host}:${port}`);
    }
    catch (err) {
        app.log.error(err);
        process.exit(1);
    }
    // Graceful shutdown
    const shutdown = async () => {
        app.log.info("Shutting down server...");
        await app.close();
        process.exit(0);
    };
    process.on("SIGINT", shutdown);
    process.on("SIGTERM", shutdown);
};
start();
