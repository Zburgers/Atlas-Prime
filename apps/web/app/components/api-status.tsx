"use client";

import { Show, SignInButton, SignUpButton, UserButton, useAuth } from "@clerk/nextjs";
import { useState } from "react";

type ApiMeResponse = {
  id: string;
  email: string | null;
  clerk_user_id: string;
};

export function AuthApiStatus({ apiBaseUrl }: { apiBaseUrl: string }) {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [result, setResult] = useState<string>("Not checked");

  async function checkApiIdentity() {
    const token = await getToken();
    if (!token) {
      setResult("No Clerk session token available");
      return;
    }

    const response = await fetch(`${apiBaseUrl}/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) {
      setResult(`API rejected session (${response.status})`);
      return;
    }

    const body = (await response.json()) as ApiMeResponse;
    setResult(`API identity: ${body.clerk_user_id}`);
  }

  return (
    <div className="authPanel">
      <div className="authControls">
        <Show when="signed-out">
          <SignInButton mode="modal">
            <button type="button">Sign in</button>
          </SignInButton>
          <SignUpButton mode="modal">
            <button type="button">Sign up</button>
          </SignUpButton>
        </Show>
        <Show when="signed-in">
          <UserButton />
          <button type="button" onClick={checkApiIdentity} disabled={!isLoaded || !isSignedIn}>
            Check API identity
          </button>
        </Show>
      </div>
      <p>
        Clerk/API status: <code>{result}</code>
      </p>
    </div>
  );
}
