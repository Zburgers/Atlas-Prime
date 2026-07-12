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
        <Link href="/">Home</Link>
        <Link href="/search">Search</Link>
        <Link href="/studio">Studio</Link>
        <Link href="/upload">Upload</Link>
        <Link href="/admin">Admin</Link>
      </nav>
      <form className="headerSearch" action="/search" method="get" role="search">
        <label className="srOnly" htmlFor="header-search">
          Search public videos
        </label>
        <input id="header-search" name="q" placeholder="Search videos" type="search" />
        <button type="submit">Search</button>
      </form>
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
