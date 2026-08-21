"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import LogoutButton from "@/components/logoutButton";
import { SendEmailForm, ReadEmailForm } from "@/components/email";
import { ScheduleEmailForm, ScheduledEmailList } from "@/components/scheduled-emails";
import { AgentChat } from "@/components/agent";
import { CalendarAgentChat, CalendarEventList, CalendarSelector, UpcomingEventsView } from "@/components/calendar";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

// Wrapper component that listens for refresh events and forces re-mount via key
function ScheduledEmailListWithRefresh({ apiUrl, token }: { apiUrl: string; token: string }) {
  const [refreshKey, setRefreshKey] = useState(0);

  const handleRefresh = useCallback(() => {
    setRefreshKey((prev) => prev + 1);
  }, []);

  useEffect(() => {
    const handler = () => handleRefresh();
    window.addEventListener("scheduled-email-refresh", handler);
    return () => window.removeEventListener("scheduled-email-refresh", handler);
  }, [handleRefresh]);

  return <ScheduledEmailList key={refreshKey} apiUrl={apiUrl} token={token} />;
}

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

export default function Dashboard() {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [googleStatus, setGoogleStatus] = useState<GoogleStatus | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const tokenFromUrl = params.get("token");

    if (tokenFromUrl) {
      window.localStorage.setItem("email_agent_token", tokenFromUrl);
      window.history.replaceState({}, "", window.location.pathname);
    }

    const storedToken = window.localStorage.getItem("email_agent_token");
    // eslint-disable-next-line react-hooks/set-state-in-effect -- Initial token load on mount is a standard pattern
    setToken(storedToken);

    if (!storedToken) {
      router.replace("/login");
      return;
    }

    // load user profile and google connection status in parallel
    const profileReq = fetch(`${API_URL}/api/auth/me`, {
      headers: { Authorization: `Bearer ${storedToken}` },
    }).then((r) => {
      if (!r.ok) throw new Error("Unauthorized");
      return r.json();
    });

    const statusReq = fetch(`${API_URL}/api/auth/google/status`, {
      headers: { Authorization: `Bearer ${storedToken}` },
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
    const currentToken = window.localStorage.getItem("email_agent_token");
    if (!currentToken) return router.replace("/login");

    try {
      setConnecting(true);
      const res = await fetch(`${API_URL}/api/auth/google/start`, {
        headers: {
          Authorization: `Bearer ${currentToken}`,
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

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-slate-600">Loading dashboard...</p>
        </div>
      </main>
    );
  }

  if (!user || !token) {
    return null;
  }

  // At this point, token is guaranteed to be non-null due to the check above
  const currentToken = token;

  return (
    <main className="min-h-screen bg-slate-50 p-8">
      {/* Header Section */}
      <div className="mx-auto max-w-7xl mb-8">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.3em] text-slate-500">Dashboard</p>
              <h1 className="mt-2 text-3xl font-semibold text-slate-900">Welcome back, {user.name}</h1>
              <p className="mt-2 text-slate-600">{user.email}</p>
            </div>
            <div className="flex flex-wrap items-center gap-4">
              {googleStatus && googleStatus.connected ? (
                <div className="rounded-md bg-green-50 px-3 py-1 text-sm text-green-700">
                  Connected: {googleStatus.email}
                </div>
              ) : (
                <div className="rounded-md bg-yellow-50 px-3 py-1 text-sm text-yellow-700">Not connected</div>
              )}

              <button
                onClick={connectGmail}
                disabled={connecting}
                className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {connecting
                  ? "Connecting..."
                  : googleStatus && googleStatus.connected
                  ? "Reconnect Gmail"
                  : "Connect Gmail"}
              </button>

              <LogoutButton />
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="mx-auto grid max-w-7xl gap-6 lg:grid-cols-2 xl:grid-cols-3">
        {/* Email Section */}
        <section aria-labelledby="email-heading" className="lg:col-span-2 xl:col-span-3">
          <h2 id="email-heading" className="sr-only">Email Features</h2>
          <div className="grid gap-6 lg:grid-cols-2">
            <SendEmailForm apiUrl={API_URL} token={currentToken} />
            <ReadEmailForm apiUrl={API_URL} token={currentToken} />
          </div>
        </section>

        {/* AI Email Assistant */}
        <section aria-labelledby="agent-heading" className="lg:col-span-2 xl:col-span-3">
          <h2 id="agent-heading" className="sr-only">AI Email Assistant</h2>
          <AgentChat
            apiUrl={API_URL}
            token={currentToken}
            endpoint="/api/agent/run"
            title="AI Email Assistant"
            subtitle="Draft, review, send, or schedule emails using natural language"
            placeholder="Schedule an email to john@example.com for tomorrow at 3pm about the meeting..."
          />
        </section>

        {/* Scheduled Emails Section */}
        <section aria-labelledby="scheduled-heading" className="lg:col-span-2 xl:col-span-3">
          <h2 id="scheduled-heading" className="sr-only">Scheduled Emails</h2>
          <div className="grid gap-6 lg:grid-cols-2">
            <ScheduleEmailForm
              apiUrl={API_URL}
              token={currentToken}
              onSuccess={() => {
                // Trigger refresh of scheduled emails list
                window.dispatchEvent(new CustomEvent("scheduled-email-refresh"));
              }}
            />
            <ScheduledEmailListWithRefresh apiUrl={API_URL} token={currentToken} />
          </div>
        </section>

        {/* Google Calendar Section */}
        <section aria-labelledby="calendar-heading" className="lg:col-span-2 xl:col-span-3">
          <h2 id="calendar-heading" className="sr-only">Google Calendar</h2>
          <div className="grid gap-6 lg:grid-cols-2">
            <CalendarAgentChat apiUrl={API_URL} token={currentToken} />
            <CalendarSelector apiUrl={API_URL} token={currentToken} />
          </div>
          <div className="grid gap-6 lg:grid-cols-2">
            <CalendarEventList apiUrl={API_URL} token={currentToken} />
            <UpcomingEventsView apiUrl={API_URL} token={currentToken} />
          </div>
        </section>
      </div>
    </main>
  );
}