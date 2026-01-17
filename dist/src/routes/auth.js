import { config } from "../env.js";
export async function registerAuthRoutes(app) {
    // Minimal token issuance for local development and testing
    app.post("/auth/token", {
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
    }, async (req, reply) => {
        const { username, password } = req.body;
        let role = null;
        if (username === config.creds.viewer.username &&
            password === config.creds.viewer.password) {
            role = "viewer";
        }
        else if (username === config.creds.operator.username &&
            password === config.creds.operator.password) {
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
    });
    // Simple decode endpoint to inspect token (optional, helpful in dev)
    app.get("/auth/me", {
        preHandler: app.requireRoles(["viewer", "operator"]),
    }, async (req) => {
        return { user: req.user };
    });
}
