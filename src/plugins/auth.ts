import fp from "fastify-plugin";
import jwt from "@fastify/jwt";
import sensible from "@fastify/sensible";
import { config } from "../env.js";
import { FastifyInstance, FastifyReply, FastifyRequest } from "fastify";

// Augment @fastify/jwt types so request.user has role
declare module "@fastify/jwt" {
  interface FastifyJWT {
    payload: { role: "viewer" | "operator"; sub?: string };
    user: { role: "viewer" | "operator"; sub?: string };
  }
}

declare module "fastify" {
  interface FastifyInstance {
    authenticate: (req: FastifyRequest, reply: FastifyReply) => Promise<void>;
    requireRoles: (
      roles: Array<"viewer" | "operator">,
    ) => (req: FastifyRequest, reply: FastifyReply) => Promise<void>;
  }
}

export default fp(async (app: FastifyInstance) => {
  // Register sensible to get httpErrors
  await app.register(sensible);

  // Register JWT plugin (only secret here)
  await app.register(jwt, {
    secret: config.jwt.secret,
  });

  // Decorators
  app.decorate(
    "authenticate",
    async (req: FastifyRequest, _reply: FastifyReply) => {
      try {
        await req.jwtVerify();
      } catch {
        throw app.httpErrors.unauthorized("Unauthorized");
      }
    },
  );

  app.decorate("requireRoles", (roles: Array<"viewer" | "operator">) => {
    return async (req: FastifyRequest, reply: FastifyReply) => {
      await app.authenticate(req, reply);

      const role = req.user?.role;
      if (!role || !roles.includes(role)) {
        throw app.httpErrors.forbidden("Forbidden");
      }
    };
  });
});
