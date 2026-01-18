import { FastifyInstance } from "fastify";
import { config } from "../env";

export async function registerAuthRoutes(app: FastifyInstance) {
  app.post(
    "/auth/token",
    {
      schema: {
        body: {
          type: "object",
          required: ["username", "password"],
          properties: {
            username: { type: "string" },
            password: { type: "string" },
          },
          additionalProperties: false,
        },
      },
    },
    async (req, reply) => {
      const { username, password } = req.body as {
        username: string;
        password: string;
      };

      let role: "viewer" | "operator" | null = null;

      if (
        username === config.creds.viewer.username &&
        password === config.creds.viewer.password
      ) {
        role = "viewer";
      } else if (
        username === config.creds.operator.username &&
        password === config.creds.operator.password
      ) {
        role = "operator";
      }

      if (!role) {
        return reply.code(401).send({ message: "Invalid credentials" });
      }

      const token = await reply.jwtSign({
        role,
        sub: username,
      });

      return {
        token,
        token_type: "Bearer",
        expires_in: config.jwt.expiresIn,
        role,
      };
    },
  );

  app.get(
    "/auth/me",
    {
      preHandler: app.requireRoles(["viewer", "operator"]),
    },
    async (req) => {
      return { user: req.user };
    },
  );
}
