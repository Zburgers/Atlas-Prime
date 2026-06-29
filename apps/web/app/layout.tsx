import "./globals.css";
import { ClerkProvider } from "@clerk/nextjs";
import type { Metadata } from "next";
import type { ReactNode } from "react";
import { AppHeader } from "./components/app-header";

export const metadata: Metadata = {
  title: "Atlas Prime",
  description: "Self-hostable VOD learning platform MVP",
};

const clerkPublishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY || process.env.CLERK_PUBLISHABLE_KEY;

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <ClerkProvider publishableKey={clerkPublishableKey}>
          <AppHeader />
          <main>{children}</main>
        </ClerkProvider>
      </body>
    </html>
  );
}
