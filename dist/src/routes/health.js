export async function registerHealthRoutes(app) {
    app.get('/health', async () => {
        return {
            status: 'ok',
            time: new Date().toISOString()
        };
    });
}
