import type { ReactNode } from "react";
import { notFound, redirect } from "next/navigation";
import { getAdminAccessStatus } from "./admin-auth";

export default async function AdminLayout({ children }: { children: ReactNode }) {
  const status = await getAdminAccessStatus();
  if (status === 401) redirect("/sign-in");
  if (status === 403) notFound();
  return children;
}
