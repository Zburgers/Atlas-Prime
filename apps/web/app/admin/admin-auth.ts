import "server-only";
import { auth } from "@clerk/nextjs/server";
import { adminAccessStatus } from "./admin-policy.mjs";

export async function getAdminAccessStatus() {
  const { userId } = await auth();
  return adminAccessStatus(userId, process.env.ATLAS_ADMIN_CLERK_USER_IDS ?? "");
}
