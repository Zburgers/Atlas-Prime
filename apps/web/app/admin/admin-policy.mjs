export function adminAccessStatus(userId, rawAllowlist) {
  if (!userId) return 401;
  const allowedIds = new Set(rawAllowlist.split(",").map((id) => id.trim()).filter(Boolean));
  return allowedIds.has(userId) ? null : 403;
}

export async function withAdminProxyAuthorization(path, getAccessStatus, forward) {
  if (path[0] !== "admin") return forward();

  const status = await getAccessStatus();
  if (status === 401) return Response.json({ error: "Unauthorized" }, { status });
  if (status === 403) return Response.json({ error: "Forbidden" }, { status });
  return forward();
}
