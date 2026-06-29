"use client";

import { Show, SignInButton, SignUpButton, UserButton, useAuth } from "@clerk/nextjs";
import { useState } from "react";
import { apiRequest } from "./video-api";

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

    try {
      const body = await apiRequest<ApiMeResponse>("/me", { token });
      setResult(`API identity: ${body.clerk_user_id}`);
    } catch {
      setResult(`API rejected session via ${apiBaseUrl}`);
    }
  }

  return (
    <div className="authPanel">
      <div className="authControls">
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
