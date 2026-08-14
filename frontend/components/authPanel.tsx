"use client";

import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function AuthPanel() {
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleGoogleLogin() {
    setError("");
    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/api/auth/google/login/start`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to start Google sign-in");
      }

      if (!data.authorization_url) {
        throw new Error("Google sign-in URL was not returned");
      }

      window.location.assign(data.authorization_url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
      setLoading(false);
    }
  }

  return (
    <div className="w-full max-w-md rounded-lg border border-slate-200 bg-white p-8 shadow-sm">
      <p className="text-sm font-medium text-slate-600">
        Sign in with your Google account to access your workspace.
      </p>

      {error ? <p className="mt-4 text-sm text-red-600">{error}</p> : null}

      <button
        type="button"
        onClick={handleGoogleLogin}
        disabled={loading}
        className="mt-6 flex w-full items-center justify-center gap-2 rounded-md bg-slate-900 px-4 py-2 font-medium text-white disabled:cursor-not-allowed disabled:opacity-70"
      >
        {loading ? "Redirecting..." : "Continue with Google"}
      </button>
    </div>
  );
}
