"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import LogoutButton from "@/components/logoutButton";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

type UserProfile = {
  id: number;
  email: string;
  name: string;
  image?: string | null;
};

interface GoogleStatus {
  connected: boolean;
  email?: string;
}

export type AgentMessage = {
  role: "user" | "model" | "tool";
  text: string;
};

export default function Dashboard() {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [googleStatus, setGoogleStatus] = useState<GoogleStatus | null>(null);
  const [sending, setSending] = useState(false);
  const [sendResult, setSendResult] = useState<string | null>(null);
  const [readResult, setReadResult] = useState<string | null>(null);
  const [readLoading, setReadLoading] = useState(false);
  const [agentPrompt, setAgentPrompt] = useState("");
  const [agentMessages, setAgentMessages] = useState<AgentMessage[]>([]);
  const [agentSessionId, setAgentSessionId] = useState<string | null>(null);
  const [agentLoading, setAgentLoading] = useState(false);
  const [agentError, setAgentError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const tokenFromUrl = params.get("token");

    if (tokenFromUrl) {
      window.localStorage.setItem("email_agent_token", tokenFromUrl);
      window.history.replaceState({}, "", window.location.pathname);
    }

    const token = window.localStorage.getItem("email_agent_token");
    if (!token) {
      router.replace("/login");
      return;
    }

    // load user profile and google connection status in parallel
    const profileReq = fetch(`${API_URL}/api/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    }).then((r) => {
      if (!r.ok) throw new Error("Unauthorized");
      return r.json();
    });

    const statusReq = fetch(`${API_URL}/api/auth/google/status`, {
      headers: { Authorization: `Bearer ${token}` },
    }).then((r) => (r.ok ? r.json() : { connected: false }));

    Promise.all([profileReq, statusReq])
      .then(([profile, status]) => {
        setUser(profile);
        setGoogleStatus(status);
      })
      .catch(() => {
        window.localStorage.removeItem("email_agent_token");
        router.replace("/login");
      })
      .finally(() => setLoading(false));
  }, [router]);

  async function connectGmail() {
    const token = window.localStorage.getItem("email_agent_token");
    if (!token) return router.replace("/login");

    try {
      setConnecting(true);
      const res = await fetch(`${API_URL}/api/auth/google/start`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!res.ok) throw new Error("Could not start Google OAuth");

      const data = await res.json();
      const url = data.authorization_url;
      if (!url) throw new Error("No authorization URL returned");

      // Redirect the browser to Google's consent screen
      window.location.href = url;
    } catch (err) {
      console.error(err);
      alert("Failed to start Google OAuth.");
    } finally {
      setConnecting(false);
    }
  }

  async function sendTestEmail(e: React.FormEvent) {
    e.preventDefault();
    setSendResult(null);
    const token = window.localStorage.getItem("email_agent_token");
    if (!token) return router.replace("/login");

    const form = new FormData(e.target as HTMLFormElement);
    const to = form.get("to") as string;
    const subject = form.get("subject") as string;
    const body = form.get("body") as string;

    setSending(true);
    try {
      const res = await fetch(`${API_URL}/api/gmail/send`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ to, subject, body }),
      });

      if (!res.ok) {
        const err = await res.text();
        setSendResult("Error: " + err);
      } else {
        const data = await res.json();
        setSendResult("Sent: " + (data.message_id || JSON.stringify(data)));
        // Refresh google status
        const statusRes = await fetch(`${API_URL}/api/auth/google/status`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (statusRes.ok) setGoogleStatus(await statusRes.json());
      }
    } catch (err) {
      setSendResult("Error: " + (err instanceof Error ? err.message : String(err)));
    } finally {
      setSending(false);
    }
  }

  async function readGmailEmails(e: React.FormEvent) {
    e.preventDefault();
    setReadResult(null);
    const token = window.localStorage.getItem("email_agent_token");
    if (!token) return router.replace("/login");

    const form = new FormData(e.target as HTMLFormElement);
    const ofUser = String(form.get("of_user") || "").trim();
    const datesRaw = String(form.get("dates") || "").trim();
    const amount = Number(form.get("amount") || 5);
    const dates = datesRaw
      .split(",")
      .map((date) => date.trim())
      .filter(Boolean);

    if (!ofUser) {
      setReadResult("Please provide the sender email.");
      return;
    }

    if (!dates.length) {
      setReadResult("Please enter at least one date in YYYY-MM-DD format.");
      return;
    }

    setReadLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/gmail/read`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ of_user: ofUser, dates, amount }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.detail ? JSON.stringify(data.detail) : "Failed to read emails");
      }

      const emailCount = data?.count ?? 0;
      const emailList = Array.isArray(data?.emails) ? data.emails : [];
      setReadResult(
        `Found ${emailCount} email${emailCount === 1 ? "" : "s"} from ${ofUser}. ` +
          (emailList.length ? JSON.stringify(emailList.slice(0, 5), null, 2) : "No matching emails found.")
      );
    } catch (err) {
      setReadResult("Error: " + (err instanceof Error ? err.message : String(err)));
    } finally {
      setReadLoading(false);
    }
  }

  async function sendAgentMessage(e: React.FormEvent) {
    e.preventDefault();
    const prompt = agentPrompt.trim();
    if (!prompt) return;

    const token = window.localStorage.getItem("email_agent_token");
    if (!token) return router.replace("/login");

    const userMessage: AgentMessage = { role: "user", text: prompt };
    setAgentPrompt("");
    setAgentError(null);
    setAgentLoading(true);

    try {
      const res = await fetch(`${API_URL}/api/agent/run`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: prompt, session_id: agentSessionId }),
      });

      if (!res.ok) {
        const errText = await res.text();
        throw new Error(errText || "Agent request failed");
      }

      const data = await res.json();
      setAgentSessionId(data.session_id);

      const nextMessages: AgentMessage[] = [];
      for (const event of data.events || []) {
        for (const part of event.content || []) {
          if (part.text) {
            const role: AgentMessage["role"] = event.author === "tool" ? "tool" : "model";
            nextMessages.push({
              role,
              text: part.text,
            });
          }
        }
      }

      setAgentMessages((current) => [...current, userMessage, ...nextMessages]);
    } catch (err) {
      setAgentError(err instanceof Error ? err.message : String(err));
    } finally {
      setAgentLoading(false);
    }
  }

  if (loading) {
    return <main className="flex min-h-screen items-center justify-center">Loading...</main>;
  }

  if (!user) {
    return null;
  }

  return (
    <main className="min-h-screen bg-slate-50 p-8">
      <div className="mx-auto grid max-w-4xl gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-sm font-semibold uppercase tracking-[0.3em] text-slate-500">Dashboard</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900">Welcome back, {user.name}</h1>
          <p className="mt-2 text-slate-600">{user.email}</p>

          <div className="mt-4 flex items-center gap-4">
            {googleStatus && googleStatus.connected ? (
              <div className="rounded-md bg-green-50 px-3 py-1 text-sm text-green-700">Connected: {googleStatus.email}</div>
            ) : (
              <div className="rounded-md bg-yellow-50 px-3 py-1 text-sm text-yellow-700">Not connected</div>
            )}

            <button onClick={connectGmail} disabled={connecting} className="rounded bg-blue-600 px-4 py-2 text-white">
              {connecting ? "Connecting..." : googleStatus && googleStatus.connected ? "Reconnect Gmail" : "Connect Gmail"}
            </button>

            <LogoutButton />
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-sm font-semibold uppercase tracking-[0.3em] text-slate-500">Send test email</p>

          <form onSubmit={sendTestEmail} className="mt-4 space-y-3">
            <div>
              <label className="mb-1 block text-sm text-slate-700">To</label>
              <input name="to" className="w-full rounded-md border border-slate-300 px-3 py-2 text-slate-900" required />
            </div>
            <div>
              <label className="mb-1 block text-sm text-slate-700">Subject</label>
              <input name="subject" className="w-full rounded-md border border-slate-300 px-3 py-2 text-slate-900" required />
            </div>
            <div>
              <label className="mb-1 block text-sm text-slate-700">Body</label>
              <textarea name="body" rows={6} className="w-full rounded-md border border-slate-300 px-3 py-2 text-slate-900" required />
            </div>

            <div className="flex items-center gap-3">
              <button type="submit" disabled={sending} className="rounded bg-slate-900 px-4 py-2 text-white">
                {sending ? "Sending..." : "Send email"}
              </button>

              {sendResult ? <p className="text-sm text-slate-700">{sendResult}</p> : null}
            </div>
          </form>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-sm font-semibold uppercase tracking-[0.3em] text-slate-500">Read Gmail</p>

          <form onSubmit={readGmailEmails} className="mt-4 space-y-3">
            <div>
              <label className="mb-1 block text-sm text-slate-700">Email of user</label>
              <input name="of_user" type="email" className="w-full rounded-md border border-slate-300 px-3 py-2 text-slate-900" placeholder="sender@example.com" required />
            </div>
            <div>
              <label className="mb-1 block text-sm text-slate-700">Dates</label>
              <input
                name="dates"
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-slate-900"
                placeholder="2026-08-01, 2026-08-03"
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-sm text-slate-700">Amount</label>
              <input name="amount" type="number" min={1} max={50} defaultValue={5} className="w-full rounded-md border border-slate-300 px-3 py-2 text-slate-900" required />
            </div>

            <div className="flex items-center gap-3">
              <button type="submit" disabled={readLoading} className="rounded bg-emerald-600 px-4 py-2 text-white disabled:cursor-not-allowed disabled:opacity-70">
                {readLoading ? "Reading..." : "Read emails"}
              </button>
            </div>

            {readResult ? (
              <pre className="mt-3 max-h-80 overflow-auto rounded-md bg-slate-100 p-3 text-xs text-slate-800 whitespace-pre-wrap">
                {readResult}
              </pre>
            ) : null}
          </form>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-sm font-semibold uppercase tracking-[0.3em] text-slate-500">AI Email Assistant</p>

          <form onSubmit={sendAgentMessage} className="mt-4 space-y-3">
            <div>
              <label className="mb-1 block text-sm text-slate-700" htmlFor="agentPrompt">
                Ask the agent to draft, review, or send an email
              </label>
              <textarea
                id="agentPrompt"
                value={agentPrompt}
                onChange={(event) => setAgentPrompt(event.target.value)}
                rows={5}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-slate-900"
                placeholder="Compose an email to the team asking for the project update..."
                required
              />
            </div>

            <div className="flex items-center gap-3">
              <button
                type="submit"
                disabled={agentLoading || !agentPrompt.trim()}
                className="rounded bg-slate-900 px-4 py-2 text-white disabled:cursor-not-allowed disabled:opacity-70"
              >
                {agentLoading ? "Thinking..." : "Send to agent"}
              </button>

              {agentError ? <p className="text-sm text-red-600">{agentError}</p> : null}
            </div>
          </form>

          {agentSessionId ? (
            <p className="mt-3 text-sm text-slate-500">Agent session id: {agentSessionId}</p>
          ) : null}

          {agentMessages.length ? (
            <div className="mt-4 space-y-3">
              {agentMessages.map((message, index) => (
                <div
                  key={`${index}-${message.role}`}
                  className={`rounded-xl border px-4 py-3 ${
                    message.role === "user"
                      ? "border-slate-200 bg-slate-50"
                      : message.role === "tool"
                      ? "border-amber-200 bg-amber-50"
                      : "border-slate-200 bg-white"
                  }`}
                >
                  <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
                    {message.role}
                  </p>
                  <p className="mt-2 whitespace-pre-wrap text-sm text-slate-800">{message.text}</p>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </main>
  );
}
