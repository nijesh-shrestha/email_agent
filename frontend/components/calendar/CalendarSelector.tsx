"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Card, CardHeader, CardContent, Select, Badge } from "@/components/ui";

interface Calendar {
  id: string;
  summary: string;
  description: string;
  primary: boolean;
  access_role: string;
  time_zone: string;
}

interface CalendarSelectorProps {
  apiUrl: string;
  token: string;
  onCalendarChange?: (calendarId: string) => void;
  selectedCalendarId?: string;
}

interface CalendarListResponse {
  calendars?: Calendar[];
  detail?: string;
}

export function CalendarSelector({ apiUrl, token, onCalendarChange, selectedCalendarId = "primary" }: CalendarSelectorProps) {
  const [calendars, setCalendars] = useState<Calendar[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCalendar, setSelectedCalendar] = useState(selectedCalendarId);

  const fetchCalendars = useCallback(async () => {
    try {
      const res = await fetch(`${apiUrl}/api/calendar/calendars`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      const data: CalendarListResponse = await res.json();
      if (!res.ok) {
        let errorMessage = data?.detail || "Failed to fetch calendars";

        // Handle insufficient calendar scope error specifically
        if (res.status === 403 && errorMessage.includes("Calendar access")) {
          errorMessage = "Google Calendar access requires additional permissions. Please reconnect your Google account to grant Calendar access.";
        }

        throw new Error(errorMessage);
      }

      setCalendars(data.calendars || []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [apiUrl, token]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void fetchCalendars();
  }, [fetchCalendars]);

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const calendarId = e.target.value;
    setSelectedCalendar(calendarId);
    onCalendarChange?.(calendarId);
  };

  return (
    <Card>
      <CardHeader title="Available Calendars" subtitle="Select a calendar to view events" />
      <CardContent>
        {loading ? (
          <p className="text-sm text-slate-500 text-center py-4">Loading calendars...</p>
        ) : error ? (
          <div className="p-3 rounded-md bg-red-50 text-red-700 text-sm" role="alert">
            {error}
          </div>
        ) : calendars.length === 0 ? (
          <p className="text-sm text-slate-500 text-center py-4">No calendars found</p>
        ) : (
          <div className="space-y-2">
            <Select
              label="Select Calendar"
              value={selectedCalendar}
              onChange={handleChange}
              options={calendars.map((cal) => ({
                value: cal.id,
                label: `${cal.summary} ${cal.primary ? " (Primary)" : ""}`,
              }))}
            />
            <div className="space-y-2">
              {calendars.map((cal) => (
                <div
                  key={cal.id}
                  className={`rounded-lg border p-3 ${
                    selectedCalendar === cal.id
                      ? "border-blue-500 bg-blue-50"
                      : "border-slate-200 bg-white"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {cal.primary && <Badge variant="info">Primary</Badge>}
                      <span className="font-medium text-slate-900">{cal.summary}</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-slate-500">
                      <Badge variant="neutral">{cal.access_role}</Badge>
                      <span>{cal.time_zone}</span>
                    </div>
                  </div>
                  {cal.description && (
                    <p className="mt-1 text-sm text-slate-600">{cal.description}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}