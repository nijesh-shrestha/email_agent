"use client";

import React, { useState } from "react";
import { Card, CardHeader, CardContent, Button, Input, Textarea, Select } from "@/components/ui";
import { formatNptDateTime, nptInputToUtc, toNptDateTimeInput } from "@/lib/timezone";

interface CreateEventFormProps {
  apiUrl: string;
  token: string;
  onSuccess?: () => void;
}

export function CreateEventForm({ apiUrl, token, onSuccess }: CreateEventFormProps) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    summary: "",
    description: "",
    location: "",
    start_datetime: "",
    end_datetime: "",
    calendar_id: "primary",
    attendees: "",
  });
  const [errors, setErrors] = useState<{ summary?: string; start_datetime?: string; end_datetime?: string }>({});

  const validateForm = () => {
    const newErrors: typeof errors = {};
    if (!formData.summary.trim()) newErrors.summary = "Event title is required";
    if (!formData.start_datetime) newErrors.start_datetime = "Start date/time is required";
    if (!formData.end_datetime) newErrors.end_datetime = "End date/time is required";
    else {
      const start = new Date(formData.start_datetime);
      const end = new Date(formData.end_datetime);
      if (end <= start) {
        newErrors.end_datetime = "End time must be after start time";
      }
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!validateForm()) return;

    setLoading(true);
    setResult(null);

    try {
      const startUtc = nptInputToUtc(formData.start_datetime);
      const endUtc = nptInputToUtc(formData.end_datetime);
      const attendees = formData.attendees
        .split(",")
        .map((e) => e.trim())
        .filter((e) => e);

      const res = await fetch(`${apiUrl}/api/calendar/events`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          ...formData,
          start_datetime: startUtc,
          end_datetime: endUtc,
          attendees: attendees.length > 0 ? attendees : undefined,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.detail || "Failed to create event");
      }

      setResult(`✓ Success: Event "${data.event?.summary}" created for ${formatNptDateTime(data.event?.start)} NPT`);
      setFormData({ summary: "", description: "", location: "", start_datetime: "", end_datetime: "", calendar_id: "primary", attendees: "" });
      onSuccess?.();
    } catch (err) {
      setResult(`✗ Error: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (errors[name as keyof typeof errors]) {
      setErrors((prev) => ({ ...prev, [name]: undefined }));
    }
  };

  // Set default datetime-local values to tomorrow at 9am and 10am
  const defaultStart = new Date();
  defaultStart.setDate(defaultStart.getDate() + 1);
  defaultStart.setHours(9, 0, 0, 0);
  const defaultStartString = toNptDateTimeInput(defaultStart);

  const defaultEnd = new Date(defaultStart);
  defaultEnd.setHours(10, 0, 0, 0);
  const defaultEndString = toNptDateTimeInput(defaultEnd);

  return (
    <Card>
      <CardHeader title="Create Calendar Event" subtitle="Add a new event to your Google Calendar" />
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            name="summary"
            label="Event Title"
            placeholder="Team meeting, Doctor appointment, etc."
            value={formData.summary}
            onChange={handleChange}
            error={errors.summary}
            required
          />
          <Textarea
            name="description"
            label="Description (optional)"
            placeholder="Event details, agenda, notes..."
            value={formData.description}
            onChange={handleChange}
            rows={3}
          />
          <Input
            name="location"
            label="Location (optional)"
            placeholder="Office, Zoom link, Address..."
            value={formData.location}
            onChange={handleChange}
          />
          <div className="grid gap-4 md:grid-cols-2">
            <Input
              name="start_datetime"
              label="Start Date & Time (NPT)"
              type="datetime-local"
              value={formData.start_datetime || defaultStartString}
              onChange={handleChange}
              error={errors.start_datetime}
              required
            />
            <Input
              name="end_datetime"
              label="End Date & Time (NPT)"
              type="datetime-local"
              value={formData.end_datetime || defaultEndString}
              onChange={handleChange}
              error={errors.end_datetime}
              required
            />
          </div>
          <Input
            name="attendees"
            label="Attendees (optional)"
            type="email"
            placeholder="attendee1@example.com, attendee2@example.com"
            value={formData.attendees}
            onChange={handleChange}
          />
          <Select
            name="calendar_id"
            label="Calendar"
            value={formData.calendar_id}
            onChange={handleChange}
            options={[{ value: "primary", label: "Primary Calendar" }]}
          />
          <div className="flex items-center gap-3 pt-2">
            <Button type="submit" variant="warning" loading={loading} disabled={loading}>
              {loading ? "Creating..." : "Create Event"}
            </Button>
            {result && <p className="text-sm text-slate-700">{result}</p>}
          </div>
        </form>
      </CardContent>
    </Card>
  );
}