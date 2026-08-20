"use client";

import React, { useState, useEffect } from "react";
import { Card, CardHeader, CardContent, Button, Input, Select, Badge } from "@/components/ui";

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

interface CalendarEventListProps {
  apiUrl: string;
  token: string;
}

export function CalendarEventList({ apiUrl, token }: CalendarEventListProps) {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    time_min: "",
    time_max: "",
    max_results: "10",
    calendar_id: "primary",
  });

  const fetchEvents = async () => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      if (formData.time_min) params.append("time_min", formData.time_min);
      if (formData.time_max) params.append("time_max", formData.time_max);
      params.append("max_results", formData.max_results);
      params.append("calendar_id", formData.calendar_id);

      const res = await fetch(`${apiUrl}/api/calendar/events?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.detail || "Failed to fetch events");
      }

      setEvents(data.events || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  // Set default date range to today
  const today = new Date().toISOString().split("T")[0];
  const nextWeek = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split("T")[0];

  return (
    <Card className="lg:col-span-2">
      <CardHeader title="Calendar Events" subtitle="View events from your Google Calendar" />
      <CardContent>
        <form onSubmit={(e) => { e.preventDefault(); fetchEvents(); }} className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            <Input
              name="time_min"
              label="Start Date"
              type="date"
              value={formData.time_min || today}
              onChange={handleChange}
            />
            <Input
              name="time_max"
              label="End Date"
              type="date"
              value={formData.time_max || nextWeek}
              onChange={handleChange}
            />
            <Input
              name="max_results"
              label="Max Results"
              type="number"
              min={1}
              max={100}
              value={formData.max_results}
              onChange={handleChange}
            />
            <Select
              name="calendar_id"
              label="Calendar"
              value={formData.calendar_id}
              onChange={handleChange}
              options={[
                { value: "primary", label: "Primary Calendar" },
                // Additional calendars would be loaded dynamically
              ]}
            />
          </div>
          <Button type="submit" variant="primary" loading={loading}>
            {loading ? "Loading..." : "Fetch Events"}
          </Button>
        </form>

        {error && (
          <div className="mt-4 p-3 rounded-md bg-red-50 text-red-700 text-sm" role="alert">
            {error}
          </div>
        )}

        {events.length > 0 && (
          <div className="mt-6 space-y-3">
            <h3 className="text-sm font-semibold text-slate-700">Events ({events.length})</h3>
            <div className="space-y-2 max-h-96 overflow-auto">
              {events.map((event) => (
                <div
                  key={event.id}
                  className="rounded-lg border border-slate-200 bg-white p-4 hover:bg-slate-50 transition-colors"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-slate-900 truncate">{event.summary || "(No title)"}</p>
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
                        {new Date(event.start).toLocaleString()} - {new Date(event.end).toLocaleString()}
                      </p>
                      {event.description && (
                        <p className="text-sm text-slate-500 mt-2 line-clamp-2">{event.description}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge
                        variant={
                          event.status === "confirmed" ? "success" :
                          event.status === "tentative" ? "warning" :
                          event.status === "cancelled" ? "danger" : "default"
                        }
                      >
                        {event.status}
                      </Badge>
                      <a
                        href={event.html_link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-blue-600 hover:underline"
                      >
                        View in Calendar
                      </a>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {!loading && events.length === 0 && !error && (
          <p className="mt-6 text-center text-slate-500">No events found for the selected date range.</p>
        )}
      </CardContent>
    </Card>
  );
}