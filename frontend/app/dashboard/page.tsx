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

interface ScheduledEmail {
  id: number;
  recipient: string;
  subject: string;
  body: string;
  scheduled_date: string;
  status: string;
  created_at: string;
  sent_at?: string | null;
  error_message?: string | null;
  message_id?: string | null;
}

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
  const [scheduledEmails, setScheduledEmails] = useState<ScheduledEmail[]>([]);
  const [scheduleLoading, setScheduleLoading] = useState(false);
  const [scheduleResult, setScheduleResult] = useState<string | null>(null);
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
    const amountRaw = String(form.get("amount") || "").trim();
    
    // Parse dates - optional, can be empty
    const dates = datesRaw
      .split(",")
      .map((date) => date.trim())
      .filter(Boolean);
    
    // Parse amount - optional, defaults to undefined if not provided (backend will use 1)
    const amount = amountRaw ? Number(amountRaw) : undefined;

    if (!ofUser) {
      setReadResult("Error: Please provide the sender email or name.");
      return;
    }

    setReadLoading(true);
    try {
      // Build request body - only include dates and amount if provided
      const requestBody: { of_user: string; dates?: string[]; amount?: number } = { of_user: ofUser };
      if (dates.length > 0) {
        requestBody.dates = dates;
      }
      if (amount !== undefined) {
        requestBody.amount = amount;
      }

      const res = await fetch(`${API_URL}/api/gmail/read`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.detail ? JSON.stringify(data.detail) : "Failed to read emails");
      }

      const emailCount = data?.count ?? 0;
      const emailList = Array.isArray(data?.emails) ? data.emails : [];
      const dateInfo = dates.length > 0 ? ` on ${dates.join(", ")}` : "";
      const amountDisplay = amount ? ` (limit ${amount})` : " (latest result by default)";
      setReadResult(
        `Found ${emailCount} email${emailCount === 1 ? "" : "s"} from ${ofUser}${dateInfo}${amountDisplay}. ` +
          (emailList.length ? JSON.stringify(emailList.slice(0, 5), null, 2) : "No matching emails found.")
      );
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err);
      setReadResult("Error: " + errorMsg);
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

  async function fetchScheduledEmails() {
    const token = window.localStorage.getItem("email_agent_token");
    if (!token) return;

    try {
      const res = await fetch(`${API_URL}/api/scheduled-emails/list`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setScheduledEmails(data.scheduled_emails || []);
      }
    } catch (err) {
      console.error("Failed to fetch scheduled emails:", err);
    }
  }

  async function scheduleEmail(e: React.FormEvent) {
    e.preventDefault();
    setScheduleResult(null);
    const token = window.localStorage.getItem("email_agent_token");
    if (!token) return router.replace("/login");

    const form = new FormData(e.target as HTMLFormElement);
    const to = form.get("schedule_to") as string;
    const subject = form.get("schedule_subject") as string;
    const body = form.get("schedule_body") as string;
    const scheduledDate = form.get("schedule_date") as string;

    if (!to || !subject || !body || !scheduledDate) {
      setScheduleResult("Error: All fields are required");
      return;
    }

    setScheduleLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/scheduled-emails/schedule`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ to, subject, body, scheduled_date: scheduledDate }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.detail || "Failed to schedule email");
      }

      setScheduleResult(`Success: Email scheduled for ${new Date(data.scheduled_date).toLocaleString()}`);
      fetchScheduledEmails();
      (e.target as HTMLFormElement).reset();
    } catch (err) {
      setScheduleResult("Error: " + (err instanceof Error ? err.message : String(err)));
    } finally {
      setScheduleLoading(false);
    }
  }

  async function cancelScheduledEmail(emailId: number) {
    const token = window.localStorage.getItem("email_agent_token");
    if (!token) return router.replace("/login");

    try {
      const res = await fetch(`${API_URL}/api/scheduled-emails/${emailId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.ok) {
        fetchScheduledEmails();
      } else {
        const data = await res.json();
        alert(data.detail || "Failed to cancel scheduled email");
      }
    } catch {
      alert("Failed to cancel scheduled email");
    }
  }

  // Fetch scheduled emails on component mount
  useEffect(() => {
    if (!user) return;

    const token = window.localStorage.getItem("email_agent_token");
    if (!token) return;

    fetch(`${API_URL}/api/scheduled-emails/list`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then((data) => setScheduledEmails(data.scheduled_emails || []))
      .catch((err) => console.error("Failed to fetch scheduled emails:", err));
  }, [user]);

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
              <label className="mb-1 block text-sm text-slate-700">Email or name of user <span className="text-red-600">*</span></label>
              <input name="of_user" className="w-full rounded-md border border-slate-300 px-3 py-2 text-slate-900" placeholder="sender@example.com or John Doe" required />
            </div>
            <div>
              <label className="mb-1 block text-sm text-slate-700">Dates <span className="text-gray-400 text-xs">(optional)</span></label>
              <input
                name="dates"
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-slate-900"
                placeholder="2026-08-01, 2026-08-03 (leave empty for all emails)"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm text-slate-700">Amount <span className="text-gray-400 text-xs">(optional, defaults to 1)</span></label>
              <input name="amount" type="number" min={1} max={50} className="w-full rounded-md border border-slate-300 px-3 py-2 text-slate-900" placeholder="5" />
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
                Ask the agent to draft, review, send, or schedule an email
              </label>
              <textarea
                id="agentPrompt"
                value={agentPrompt}
                onChange={(event) => setAgentPrompt(event.target.value)}
                rows={5}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-slate-900"
                placeholder="Schedule an email to john@example.com for tomorrow at 3pm about the meeting..."
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

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-sm font-semibold uppercase tracking-[0.3em] text-slate-500">Schedule Email</p>

          <form onSubmit={scheduleEmail} className="mt-4 space-y-3">
            <div>
              <label className="mb-1 block text-sm text-slate-700">To</label>
              <input name="schedule_to" type="email" className="w-full rounded-md border border-slate-300 px-3 py-2 text-slate-900" required />
            </div>
            <div>
              <label className="mb-1 block text-sm text-slate-700">Subject</label>
              <input name="schedule_subject" className="w-full rounded-md border border-slate-300 px-3 py-2 text-slate-900" required />
            </div>
            <div>
              <label className="mb-1 block text-sm text-slate-700">Body</label>
              <textarea name="schedule_body" rows={4} className="w-full rounded-md border border-slate-300 px-3 py-2 text-slate-900" required />
            </div>
            <div>
              <label className="mb-1 block text-sm text-slate-700">Schedule Date & Time (UTC)</label>
              <input
                name="schedule_date"
                type="datetime-local"
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-slate-900"
                required
              />
            </div>

            <div className="flex items-center gap-3">
              <button type="submit" disabled={scheduleLoading} className="rounded bg-purple-600 px-4 py-2 text-white disabled:opacity-70">
                {scheduleLoading ? "Scheduling..." : "Schedule email"}
              </button>

              {scheduleResult ? <p className="text-sm text-slate-700">{scheduleResult}</p> : null}
            </div>
          </form>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold uppercase tracking-[0.3em] text-slate-500">Scheduled Emails</p>
            <button
              onClick={() => fetchScheduledEmails()}
              className="text-sm text-blue-600 hover:underline"
            >
              Refresh
            </button>
          </div>

          <div className="mt-4 space-y-3">
            {scheduledEmails.length === 0 ? (
              <p className="text-sm text-slate-500">No scheduled emails</p>
            ) : (
              scheduledEmails.map((email) => (
                <div
                  key={email.id}
                  className="rounded-lg border border-slate-200 bg-slate-50 p-4"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <p className="text-sm font-medium text-slate-900">To: {email.recipient}</p>
                      <p className="text-sm text-slate-700">Subject: {email.subject}</p>
                      <p className="text-xs text-slate-500 mt-1">
                        Scheduled: {new Date(email.scheduled_date).toLocaleString()}
                      </p>
                      <span
                        className={`inline-block mt-2 rounded px-2 py-0.5 text-xs font-medium ${
                          email.status === "pending"
                            ? "bg-yellow-100 text-yellow-800"
                            : email.status === "sent"
                            ? "bg-green-100 text-green-800"
                            : email.status === "failed"
                            ? "bg-red-100 text-red-800"
                            : "bg-gray-100 text-gray-800"
                        }`}
                      >
                        {email.status}
                      </span>
                    </div>
                    {email.status === "pending" && (
                      <button
                        onClick={() => cancelScheduledEmail(email.id)}
                        className="ml-4 text-sm text-red-600 hover:underline"
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
