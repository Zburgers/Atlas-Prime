export function adminAccessStatus(userId: string | null, rawAllowlist: string): 401 | 403 | null;
export function withAdminProxyAuthorization<T extends Response>(
  path: string[],
  getAccessStatus: () => Promise<401 | 403 | null>,
  forward: () => Promise<T>,
): Promise<T | Response>;
