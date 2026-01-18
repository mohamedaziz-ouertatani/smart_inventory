import Fastify from "fastify";
import { config } from "./env";
import dbPlugin from "./plugins/db";
import authPlugin from "./plugins/auth";
import { registerHealthRoutes } from "./routes/health";
import { registerAuthRoutes } from "./routes/auth";
import { registerForecastRoutes } from "./routes/forecasts";
import { registerRecommendationRoutes } from "./routes/recommendations";

async function buildServer() {
  const app = Fastify({
    logger: { level: config.nodeEnv === "development" ? "debug" : "info" },
  });

  await app.register(dbPlugin);
  await app.register(authPlugin);

  await registerHealthRoutes(app); // public
  await registerAuthRoutes(app); // token issuance, whoami
  await registerForecastRoutes(app); // protected
  await registerRecommendationRoutes(app); // protected

  return app;
}

const start = async () => {
  const app = await buildServer();
  try {
    await app.listen({ port: config.port, host: config.host });
    app.log.info(`Server listening on http://${config.host}:${config.port}`);
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
};

start();
