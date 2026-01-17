import fp from "fastify-plugin";
import { Pool } from "pg";
import { config } from "../env.js";

declare module "fastify" {
  interface FastifyInstance {
    db: Pool;
  }
}

async function ping(pool: Pool, attempts = 10, delayMs = 1000): Promise<void> {
  let lastErr: unknown;
  for (let i = 0; i < attempts; i++) {
    try {
      await pool.query("SELECT 1");
      return;
    } catch (err) {
      lastErr = err;
      await new Promise((res) => setTimeout(res, delayMs));
    }
  }
  throw lastErr ?? new Error("Database connectivity check failed");
}

export default fp(async (fastify) => {
  const pool = new Pool({
    host: config.pg.host,
    port: config.pg.port,
    database: config.pg.database,
    user: config.pg.user,
    password: config.pg.password,
    ssl: config.pg.ssl,
  });

  // retry ping to handle container start timing
  try {
    await ping(pool, 20, 1000); // ~20s max
    fastify.log.info("Connected to PostgreSQL");
  } catch (err) {
    fastify.log.error({ err }, "Failed to connect to PostgreSQL");
    throw err; // fail fast with clear logs
  }

  fastify.decorate("db", pool);

  fastify.addHook("onClose", async () => {
    await pool.end();
  });
});
