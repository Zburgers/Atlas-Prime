import "./globals.css";
import { ClerkProvider } from "@clerk/nextjs";
import type { Metadata } from "next";
import { connection } from "next/server";
import type { ReactNode } from "react";
import { AppHeader } from "./components/app-header";

export const metadata: Metadata = {
  title: "Atlas Prime",
  description: "Self-hostable VOD learning platform MVP",
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  await connection();

  const smokeMode = process.env.ATLAS_CI_SMOKE_MODE === "true";
  const clerkPublishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY || process.env.CLERK_PUBLISHABLE_KEY || "";
  if (!smokeMode && !clerkPublishableKey) {
    throw new Error("Clerk publishable key is required outside CI smoke mode.");
  }

  const appShell = (
    <>
      {smokeMode ? (
        <header className="appHeader">
          {/* eslint-disable-next-line @next/next/no-html-link-for-pages */}
          <a className="brand" href="/">Atlas Prime</a>
        </header>
      ) : <AppHeader />}
      <a className="skipLink" href="#main-content">Skip to main content</a>
      <main id="main-content" tabIndex={-1}>
        {smokeMode ? (
          <section className="surface" aria-labelledby="smoke-heading">
            <h1 id="smoke-heading">Atlas Prime</h1>
          </section>
        ) : children}
      </main>
    </>
  );

  return (
    <html lang="en">
      <body>
        {smokeMode ? appShell : <ClerkProvider publishableKey={clerkPublishableKey}>{appShell}</ClerkProvider>}
      </body>
    </html>
  );
}
