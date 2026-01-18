"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.registerAuthRoutes = registerAuthRoutes;
const env_js_1 = require("../env.js");
async function registerAuthRoutes(app) {
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
        if (username === env_js_1.config.creds.viewer.username &&
            password === env_js_1.config.creds.viewer.password) {
            role = "viewer";
        }
        else if (username === env_js_1.config.creds.operator.username &&
            password === env_js_1.config.creds.operator.password) {
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
            expires_in: env_js_1.config.jwt.expiresIn,
            role,
        };
    });
    app.get("/auth/me", {
        preHandler: app.requireRoles(["viewer", "operator"]),
    }, async (req) => {
        return { user: req.user };
    });
}
