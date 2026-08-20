"use client";

import React, { useEffect, useState } from "react";
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

  const fetchScheduledEmails = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiUrl}/api/scheduled-emails/list`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setScheduledEmails(data.scheduled_emails || []);
      }
    } catch (err) {
      console.error("Failed to fetch scheduled emails:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchScheduledEmails();
  }, [apiUrl, token]);

  const cancelScheduledEmail = async (emailId: number) => {
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
        {loading ? (
          <p className="text-sm text-slate-500 text-center py-4">Loading...</p>
        ) : scheduledEmails.length === 0 ? (
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
                      Scheduled: {new Date(email.scheduled_date).toLocaleString()}
                    </p>
                    {getStatusBadge(email.status)}
                  </div>
                  {email.status === "pending" && (
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={() => cancelScheduledEmail(email.id)}
                    >
                      Cancel
                    </Button>
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