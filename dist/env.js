"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.config = void 0;
const dotenv_1 = __importDefault(require("dotenv"));
dotenv_1.default.config();
function bool(v, def) {
    if (v === undefined)
        return def;
    return ["1", "true", "yes", "y"].includes(v.toLowerCase());
}
exports.config = {
    port: Number(process.env.PORT ?? 3000),
    host: process.env.HOST ?? "0.0.0.0",
    nodeEnv: process.env.NODE_ENV ?? "development",
    pg: {
        host: process.env.PGHOST ?? "localhost",
        port: Number(process.env.PGPORT ?? 5432),
        database: process.env.PGDATABASE ?? "smart_inventory",
        user: process.env.PGUSER ?? "postgres",
        password: process.env.PGPASSWORD ?? "0000",
        ssl: bool(process.env.PGSSL, false)
            ? { rejectUnauthorized: false }
            : undefined,
    },
    jwt: {
        secret: process.env.JWT_SECRET ?? "change-me",
        issuer: process.env.JWT_ISSUER ?? "smart-inventory",
        expiresIn: process.env.JWT_EXPIRES_IN ?? "12h",
    },
    creds: {
        viewer: {
            username: process.env.VIEWER_USERNAME ?? "viewer",
            password: process.env.VIEWER_PASSWORD ?? "viewer123",
        },
        operator: {
            username: process.env.OPERATOR_USERNAME ?? "operator",
            password: process.env.OPERATOR_PASSWORD ?? "operator123",
        },
    },
};
