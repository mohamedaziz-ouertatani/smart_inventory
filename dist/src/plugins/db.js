import fp from 'fastify-plugin';
import { Pool } from 'pg';
import { config } from '../env.js';
export default fp(async (fastify) => {
    const pool = new Pool({
        host: config.pg.host,
        port: config.pg.port,
        database: config.pg.database,
        user: config.pg.user,
        password: config.pg.password,
        ssl: config.pg.ssl
    });
    // simple connectivity check on startup
    await pool.query('SELECT 1');
    fastify.decorate('db', pool);
    fastify.addHook('onClose', async () => {
        await pool.end();
    });
});
