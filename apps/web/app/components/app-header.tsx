"use client";

import { Show, SignInButton, SignUpButton, UserButton } from "@clerk/nextjs";
import Link from "next/link";

export function AppHeader() {
  return (
    <header className="appHeader">
      <Link className="brand" href="/">
        Atlas Prime
      </Link>
      <nav aria-label="Primary navigation">
        <Link href="/">Library</Link>
        <Link href="/upload">Upload</Link>
        <Link href="/admin">Admin</Link>
      </nav>
      <div className="headerAuth">
        <Show when="signed-out">
          <SignInButton mode="modal">
            <button className="ghostButton" type="button">
              Sign in
            </button>
          </SignInButton>
          <SignUpButton mode="modal">
            <button type="button">Sign up</button>
          </SignUpButton>
        </Show>
        <Show when="signed-in">
          <UserButton />
        </Show>
      </div>
    </header>
  );
}
