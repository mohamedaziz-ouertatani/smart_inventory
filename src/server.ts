import Fastify from "fastify";
import dotenv from "dotenv";
import { config } from "./env.js";
import dbPlugin from "./plugins/db.js";
import authPlugin from "./plugins/auth.js";
import { registerAuthRoutes } from "./routes/auth.js";
import { registerForecastRoutes } from "./routes/forecasts.js";
import { registerRecommendationRoutes } from "./routes/recommendations.js";

dotenv.config();

async function buildServer() {
  const app = Fastify({
    logger: {
      level: config.nodeEnv === "development" ? "debug" : "info",
    },
  });

  // Register plugins
  await app.register(dbPlugin);
  await app.register(authPlugin);

  // Built-in health route
  app.get("/health", async (_req, reply) => {
    app.log.info("Health check called");
    reply.send({
      status: "ok",
      time: new Date().toISOString(),
    });
  });

  // Auth routes (token issuance, whoami)
  await registerAuthRoutes(app);

  // Protected routes
  await registerForecastRoutes(app);
  await registerRecommendationRoutes(app);

  // Print all registered routes to logs
  console.log(app.printRoutes());

  return app;
}

const start = async () => {
  const app = await buildServer();
  const port = config.port || 3000;
  const host = config.host || "0.0.0.0";

  try {
    await app.listen({ port, host });
    app.log.info(`Server listening on http://${host}:${port}`);
  } catch (err) {
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
