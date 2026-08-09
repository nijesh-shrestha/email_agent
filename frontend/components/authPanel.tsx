"use client";

import { type FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

type AuthMode = "login" | "register";

export default function AuthPanel() {
  const [mode, setMode] = useState<AuthMode>("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/api/auth/${mode}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(
          mode === "register"
            ? { email, password, name }
            : { email, password }
        ),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Authentication failed");
      }

      window.localStorage.setItem("email_agent_token", data.access_token);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="w-full max-w-md rounded-lg border border-slate-200 bg-white p-8 shadow-sm">
      <div className="mb-6 flex gap-2 rounded-full bg-slate-100 p-1">
        <button
          type="button"
          onClick={() => setMode("login")}
          className={`flex-1 rounded-full px-4 py-2 text-sm font-medium ${
            mode === "login" ? "bg-slate-900 text-white" : "text-slate-600"
          }`}
        >
          Log in
        </button>
        <button
          type="button"
          onClick={() => setMode("register")}
          className={`flex-1 rounded-full px-4 py-2 text-sm font-medium ${
            mode === "register" ? "bg-slate-900 text-white" : "text-slate-600"
          }`}
        >
          Register
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {mode === "register" ? (
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="name">
              Name
            </label>
            <input
              id="name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2"
              placeholder="Alex"
            />
          </div>
        ) : null}

        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="email">
            Email
          </label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2"
            placeholder="you@example.com"
            required
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="password">
            Password
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2"
            placeholder="At least 8 characters"
            required
          />
        </div>

        {error ? <p className="text-sm text-red-600">{error}</p> : null}

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-md bg-slate-900 px-4 py-2 font-medium text-white disabled:cursor-not-allowed disabled:opacity-70"
        >
          {loading ? "Please wait..." : mode === "login" ? "Log in" : "Create account"}
        </button>
      </form>
    </div>
  );
}
