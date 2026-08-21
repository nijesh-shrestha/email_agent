"use client";

import { useEffect, useState } from "react";
import { Card, CardHeader, CardContent, Button, Badge } from "@/components/ui";

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

interface ScheduledEmailListProps {
  apiUrl: string;
  token: string;
  onRefresh?: () => void;
}

export function ScheduledEmailList({ apiUrl, token, onRefresh }: ScheduledEmailListProps) {
  const [scheduledEmails, setScheduledEmails] = useState<ScheduledEmail[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cancelLoadingId, setCancelLoadingId] = useState<number | null>(null);
  const [showCancelConfirm, setShowCancelConfirm] = useState<number | null>(null);

  const fetchScheduledEmails = async () => {
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${apiUrl}/api/scheduled-emails/list`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) {
        const data = await res.json();
        setError(data.detail || "Failed to fetch scheduled emails");
        return;
      }

      const data = await res.json();
      setScheduledEmails(data.scheduled_emails || []);
    } catch (err) {
      console.error("Failed to fetch scheduled emails:", err);
      setError("Failed to fetch scheduled emails. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let active = true;

    const loadScheduledEmails = async () => {
      setLoading(true);
      setError(null);

      try {
        const res = await fetch(`${apiUrl}/api/scheduled-emails/list`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (!active) return;

        if (!res.ok) {
          const data = await res.json();
          if (active) setError(data.detail || "Failed to fetch scheduled emails");
          return;
        }

        const data = await res.json();
        if (active) setScheduledEmails(data.scheduled_emails || []);
      } catch (err) {
        console.error("Failed to fetch scheduled emails:", err);
        if (active) {
          setError("Failed to fetch scheduled emails. Please try again.");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    void loadScheduledEmails();

    return () => {
      active = false;
    };
  }, [apiUrl, token]);

  const handleCancelClick = (emailId: number) => {
    setShowCancelConfirm(emailId);
  };

  const confirmCancel = async (emailId: number) => {
    setCancelLoadingId(emailId);
    try {
      const res = await fetch(`${apiUrl}/api/scheduled-emails/${emailId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.ok) {
        fetchScheduledEmails();
        onRefresh?.();
      } else {
        const data = await res.json();
        alert(data.detail || "Failed to cancel scheduled email");
      }
    } catch {
      alert("Failed to cancel scheduled email");
    } finally {
      setCancelLoadingId(null);
      setShowCancelConfirm(null);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "pending":
        return <Badge variant="warning">Pending</Badge>;
      case "sent":
        return <Badge variant="success">Sent</Badge>;
      case "failed":
        return <Badge variant="danger">Failed</Badge>;
      case "cancelled":
        return <Badge variant="neutral">Cancelled</Badge>;
      default:
        return <Badge variant="default">{status}</Badge>;
    }
  };

  const formatDateWithTimezone = (dateString: string) => {
    const date = new Date(dateString);
    return `${date.toLocaleString()} (local)`;
  };

  if (loading && scheduledEmails.length === 0) {
    return (
      <Card>
        <CardHeader
          title="Scheduled Emails"
          action={
            <Button variant="ghost" size="sm" onClick={fetchScheduledEmails} disabled={loading}>
              {loading ? "Refreshing..." : "Refresh"}
            </Button>
          }
        />
        <CardContent>
          <p className="text-sm text-slate-500 text-center py-4">Loading...</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader
        title="Scheduled Emails"
        action={
          <Button variant="ghost" size="sm" onClick={fetchScheduledEmails} disabled={loading}>
            {loading ? "Refreshing..." : "Refresh"}
          </Button>
        }
      />
      <CardContent>
        {error && (
          <div className="mb-4 p-3 rounded-md bg-red-50 border border-red-200">
            <p className="text-sm text-red-700" role="alert">
              {error}
            </p>
            <Button variant="ghost" size="sm" className="mt-2" onClick={fetchScheduledEmails}>
              Retry
            </Button>
          </div>
        )}
        {scheduledEmails.length === 0 && !error && !loading ? (
          <p className="text-sm text-slate-500 text-center py-4">No scheduled emails</p>
        ) : (
          <div className="space-y-3">
            {scheduledEmails.map((email) => (
              <div
                key={email.id}
                className="rounded-lg border border-slate-200 bg-slate-50 p-4"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-900 truncate">
                      To: {email.recipient}
                    </p>
                    <p className="text-sm text-slate-700 truncate mt-1">
                      Subject: {email.subject}
                    </p>
                    <p className="text-xs text-slate-500 mt-1">
                      Scheduled: {formatDateWithTimezone(email.scheduled_date)}
                    </p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Created: {formatDateWithTimezone(email.created_at)}
                    </p>
                    {email.status === "failed" && email.error_message && (
                      <p className="text-xs text-red-600 mt-1">
                        Error: {email.error_message}
                      </p>
                    )}
                    {getStatusBadge(email.status)}
                  </div>
                  {email.status === "pending" && (
                    <>
                      {showCancelConfirm === email.id ? (
                        <div className="flex items-center gap-2">
                          <p className="text-sm text-slate-700">Cancel this email?</p>
                          <Button
                            variant="danger"
                            size="sm"
                            onClick={() => confirmCancel(email.id)}
                            loading={cancelLoadingId === email.id}
                          >
                            Yes, Cancel
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setShowCancelConfirm(null)}
                            disabled={cancelLoadingId === email.id}
                          >
                            No
                          </Button>
                        </div>
                      ) : (
                        <Button
                          variant="danger"
                          size="sm"
                          onClick={() => handleCancelClick(email.id)}
                        >
                          Cancel
                        </Button>
                      )}
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
