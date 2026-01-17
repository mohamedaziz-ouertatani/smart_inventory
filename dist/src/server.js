import Fastify from "fastify";
import { config } from "./env.js";
import dbPlugin from "./plugins/db.js";
import authPlugin from "./plugins/auth.js";
import { registerHealthRoutes } from "./routes/health.js";
import { registerAuthRoutes } from "./routes/auth.js";
import { registerForecastRoutes } from "./routes/forecasts.js";
import { registerRecommendationRoutes } from "./routes/recommendations.js";
async function buildServer() {
    const app = Fastify({
        logger: {
            level: config.nodeEnv === "development" ? "debug" : "info",
        },
    });
    await app.register(dbPlugin);
    await app.register(authPlugin);
    // Public route
    await registerHealthRoutes(app);
    // Auth routes (token issuance, whoami)
    await registerAuthRoutes(app);
    // Protected routes
    await registerForecastRoutes(app);
    await registerRecommendationRoutes(app);
    return app;
}
const start = async () => {
    const app = await buildServer();
    try {
        await app.listen({ port: config.port, host: config.host });
        app.log.info(`Server listening on http://${config.host}:${config.port}`);
    }
    catch (err) {
        app.log.error(err);
        process.exit(1);
    }
};
start();
