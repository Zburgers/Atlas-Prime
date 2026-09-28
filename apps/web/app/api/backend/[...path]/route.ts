import { NextRequest } from "next/server";
import { getAdminAccessStatus } from "../../../admin/admin-auth";
import { withAdminProxyAuthorization } from "../../../admin/admin-policy.mjs";

type RouteContext = {
  params: Promise<{ path: string[] }>;
};

const apiBaseUrl =
  process.env.ATLAS_API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://localhost:8000";

async function proxyRequest(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return withAdminProxyAuthorization(path, getAdminAccessStatus, async () => {
    const target = new URL(path.join("/"), apiBaseUrl);
    target.search = request.nextUrl.search;

    const headers = new Headers(request.headers);
    headers.delete("host");
    headers.delete("connection");
    headers.delete("content-length");

    const init: RequestInit & { duplex?: "half" } = {
      method: request.method,
      headers,
      body: request.method === "GET" || request.method === "HEAD" ? undefined : request.body,
      duplex: request.method === "GET" || request.method === "HEAD" ? undefined : "half",
    };

    const response = await fetch(target, init);
    const responseHeaders = new Headers(response.headers);
    responseHeaders.delete("content-encoding");
    responseHeaders.delete("transfer-encoding");

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  });
}

export const GET = proxyRequest;
export const POST = proxyRequest;
export const PATCH = proxyRequest;
export const DELETE = proxyRequest;
