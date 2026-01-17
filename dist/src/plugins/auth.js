import fp from "fastify-plugin";
import jwt from "@fastify/jwt";
import sensible from "@fastify/sensible";
import { config } from "../env.js";
export default fp(async (app) => {
    // Register sensible to get httpErrors
    await app.register(sensible);
    // Register JWT plugin (only secret here)
    await app.register(jwt, {
        secret: config.jwt.secret,
    });
    // Decorators
    app.decorate("authenticate", async (req, _reply) => {
        try {
            await req.jwtVerify();
        }
        catch {
            throw app.httpErrors.unauthorized("Unauthorized");
        }
    });
    app.decorate("requireRoles", (roles) => {
        return async (req, reply) => {
            await app.authenticate(req, reply);
            const role = req.user?.role;
            if (!role || !roles.includes(role)) {
                throw app.httpErrors.forbidden("Forbidden");
            }
        };
    });
});
