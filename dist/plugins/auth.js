"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const fastify_plugin_1 = __importDefault(require("fastify-plugin"));
const jwt_1 = __importDefault(require("@fastify/jwt"));
const sensible_1 = __importDefault(require("@fastify/sensible"));
const env_js_1 = require("../env.js");
exports.default = (0, fastify_plugin_1.default)(async (app) => {
    // Register sensible to get httpErrors
    await app.register(sensible_1.default);
    // Register JWT plugin
    await app.register(jwt_1.default, {
        secret: env_js_1.config.jwt.secret,
        sign: {
            issuer: env_js_1.config.jwt.issuer,
            expiresIn: env_js_1.config.jwt.expiresIn,
        },
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
