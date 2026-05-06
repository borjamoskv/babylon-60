/**
 * Cloudflare Pages advanced-mode worker.
 *
 * Purpose:
 * - Serve the static landing from Cloudflare Pages.
 * - Proxy /v1/* to the Vercel FastAPI deployment that hosts CORTEX API routes.
 *
 * Required Cloudflare Pages environment variable:
 * - CORTEX_API_ORIGIN=https://your-cortex-api.vercel.app
 */

export default {
    async fetch(request, env) {
        const url = new URL(request.url);

        if (url.pathname.startsWith("/v1/")) {
            const apiOrigin = env.CORTEX_API_ORIGIN;
            if (!apiOrigin) {
                return Response.json(
                    { detail: "CORTEX_API_ORIGIN is not configured for the Cloudflare edge proxy." },
                    { status: 503 },
                );
            }

            const upstreamUrl = new URL(url.pathname + url.search, apiOrigin);
            const headers = new Headers(request.headers);
            headers.set("X-CORTEX-Edge", "cloudflare-pages");
            headers.set("X-Forwarded-Host", url.host);
            headers.delete("host");

            const init = {
                method: request.method,
                headers,
                redirect: "manual",
            };

            if (request.method !== "GET" && request.method !== "HEAD") {
                init.body = request.body;
            }

            const upstreamResponse = await fetch(new Request(upstreamUrl, init));
            const responseHeaders = new Headers(upstreamResponse.headers);
            responseHeaders.set("X-CORTEX-Proxy", "cloudflare-pages");

            return new Response(upstreamResponse.body, {
                status: upstreamResponse.status,
                statusText: upstreamResponse.statusText,
                headers: responseHeaders,
            });
        }

        return env.ASSETS.fetch(request);
    },
};
