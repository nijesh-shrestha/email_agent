"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Card, CardHeader, CardContent, Button, Input, Badge } from "@/components/ui";
import { formatNptDateTime } from "@/lib/timezone";

interface CalendarEvent {
  id: string;
  summary: string;
  description: string;
  location: string;
  start: string;
  end: string;
  status: string;
  html_link: string;
  creator: string;
  organizer: string;
}

interface UpcomingEventsViewProps {
  apiUrl: string;
  token: string;
  defaultDays?: number;
}

interface UpcomingEventsResponse {
  events?: CalendarEvent[];
  detail?: string;
}

export function UpcomingEventsView({ apiUrl, token, defaultDays = 7 }: UpcomingEventsViewProps) {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [days, setDays] = useState(defaultDays);
  const [maxResults, setMaxResults] = useState(20);
  const calendarId = "primary";

  const fetchEvents = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      params.append("days", days.toString());
      params.append("max_results", maxResults.toString());
      params.append("calendar_id", calendarId);

      const res = await fetch(`${apiUrl}/api/calendar/events/upcoming?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      const data: UpcomingEventsResponse = await res.json();
      if (!res.ok) {
        let errorMessage = data?.detail || "Failed to fetch upcoming events";

        // Handle insufficient calendar scope error specifically
        if (res.status === 403 && errorMessage.includes("Calendar access")) {
          errorMessage = "Google Calendar access requires additional permissions. Please reconnect your Google account to grant Calendar access.";
        }

        throw new Error(errorMessage);
      }

      setEvents(data.events || []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [apiUrl, token, days, maxResults, calendarId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void fetchEvents();
  }, [fetchEvents]);

  // Listen for refresh events
  useEffect(() => {
    const handleRefresh = () => fetchEvents();
    window.addEventListener("calendar-refresh", handleRefresh);
    return () => window.removeEventListener("calendar-refresh", handleRefresh);
  }, [fetchEvents]);

  const handleDaysChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = Math.max(1, Math.min(365, Number(e.target.value) || 1));
    setLoading(true);
    setDays(value);
  };

  const handleMaxResultsChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = Math.max(1, Math.min(100, Number(e.target.value) || 1));
    setLoading(true);
    setMaxResults(value);
  };

  const handleRefresh = () => {
    setLoading(true);
    void fetchEvents();
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "confirmed":
        return <Badge variant="success">Confirmed</Badge>;
      case "tentative":
        return <Badge variant="warning">Tentative</Badge>;
      case "cancelled":
        return <Badge variant="danger">Cancelled</Badge>;
      default:
        return <Badge variant="default">{status}</Badge>;
    }
  };

  return (
    <Card className="lg:col-span-2">
      <CardHeader
        title="Upcoming Events"
        subtitle={`Next ${days} day${days !== 1 ? "s" : ""}`}
        action={
          <div className="flex items-center gap-2">
            <Input
              label="Days ahead"
              type="number"
              min={1}
              max={365}
              value={days}
              onChange={handleDaysChange}
              className="w-24"
            />
            <Input
              label="Max results"
              type="number"
              min={1}
              max={100}
              value={maxResults}
              onChange={handleMaxResultsChange}
              className="w-28"
            />
            <Button variant="secondary" size="sm" onClick={handleRefresh} disabled={loading}>
              {loading ? "Refreshing..." : "Refresh"}
            </Button>
          </div>
        }
      />
      <CardContent>
        {loading ? (
          <p className="text-sm text-slate-500 text-center py-4">Loading upcoming events...</p>
        ) : error ? (
          <div className="p-3 rounded-md bg-red-50 text-red-700 text-sm" role="alert">
            {error}
          </div>
        ) : events.length === 0 ? (
          <p className="text-sm text-slate-500 text-center py-4">No upcoming events found</p>
        ) : (
          <div className="space-y-2 max-h-96 overflow-auto">
            {events.map((event) => (
              <div
                key={event.id}
                className="rounded-lg border border-slate-200 bg-white p-4 hover:bg-slate-50 transition-colors"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="font-medium text-slate-900 truncate">{event.summary || "(No title)"}</p>
                      {getStatusBadge(event.status)}
                    </div>
                    {event.location && (
                      <p className="text-sm text-slate-600 mt-1 flex items-center gap-1">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                        {event.location}
                      </p>
                    )}
                    <p className="text-sm text-slate-500 mt-1 flex items-center gap-1">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      {formatNptDateTime(event.start)} - {formatNptDateTime(event.end)} NPT
                    </p>
                    {event.description && (
                      <p className="text-sm text-slate-500 mt-2 line-clamp-2">{event.description}</p>
                    )}
                  </div>
                  <a
                    href={event.html_link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-blue-600 hover:underline whitespace-nowrap"
                  >
                    View in Calendar
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}