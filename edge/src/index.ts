export interface Env {
    MTK_TENANTS: KVNamespace;
    CORTEX_BACKEND_URL: string;
}

export default {
    async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
        if (request.method !== "POST") {
            return new Response("Method not allowed", { status: 405 });
        }

        const authHeader = request.headers.get("Authorization");
        if (!authHeader || !authHeader.startsWith("Bearer ")) {
            return new Response("Unauthorized", { status: 401 });
        }

        const apiKey = authHeader.split(" ")[1];
        
        // Edge MTK Validation (C5-REAL)
        const tenantData = await env.MTK_TENANTS.get(apiKey, "json");
        if (!tenantData) {
            return new Response("Invalid MTK Token or Quota Exceeded", { status: 403 });
        }

        const payload = await request.json();
        
        // Asynchronously forward to the Rust/SQLite backend (Zero blocking)
        ctx.waitUntil(
            fetch(env.CORTEX_BACKEND_URL, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-Cortex-Tenant": (tenantData as any).tenantId
                },
                body: JSON.stringify(payload)
            })
        );

        return new Response(JSON.stringify({ status: "queued", exergy: "maximized" }), {
            status: 202,
            headers: { "Content-Type": "application/json" }
        });
    }
};
