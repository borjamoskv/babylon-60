/**
 * Cloudflare Pages advanced-mode worker.
 *
 * Purpose:
 * - Serve the static landing from Cloudflare Pages.
 * - Proxy /v1/* to the Vercel FastAPI deployment that hosts CORTEX API routes.
 *
 * Required Cloudflare Pages environment variable:
 * - CORTEX_API_ORIGIN=https://your-cortex-api.vercel.app
 *
 * Optional Cloudflare Pages secret:
 * - VERCEL_AUTOMATION_BYPASS_SECRET=...
 */

export default {
    async fetch(request, env) {
        const url = new URL(request.url);
        const orgHosts = new Set(["cortexpersist.org", "www.cortexpersist.org"]);
        const orgSinglePageRoutes = new Set([
            "/",
            "/index.html",
            "/governance/",
            "/research/",
            "/security-posture/",
            "/evidence/",
        ]);

        if (orgHosts.has(url.hostname.toLowerCase()) && orgSinglePageRoutes.has(url.pathname)) {
            const orgUrl = new URL("/org/index.html", url);
            return env.ASSETS.fetch(new Request(orgUrl, request));
        }

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
            headers.delete("x-vercel-protection-bypass");
            headers.delete("x-vercel-set-bypass-cookie");

            if (env.VERCEL_AUTOMATION_BYPASS_SECRET) {
                headers.set("x-vercel-protection-bypass", env.VERCEL_AUTOMATION_BYPASS_SECRET);
            }

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
