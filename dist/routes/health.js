"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.registerHealthRoutes = registerHealthRoutes;
async function registerHealthRoutes(app) {
    app.get("/health", async () => {
        return {
            status: "ok",
            time: new Date().toISOString(),
        };
    });
}
