"use client";

import React, { useState } from "react";
import { Card, CardHeader, CardContent, CardFooter, Button, Input, Textarea } from "@/components/ui";

interface ScheduledEmailFormProps {
  apiUrl: string;
  token: string;
  onSuccess?: () => void;
}

export function ScheduleEmailForm({ apiUrl, token, onSuccess }: ScheduledEmailFormProps) {
  const [scheduleLoading, setScheduleLoading] = useState(false);
  const [scheduleResult, setScheduleResult] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    to: "",
    subject: "",
    body: "",
    scheduled_date: "",
  });
  const [errors, setErrors] = useState<{ to?: string; subject?: string; body?: string; scheduled_date?: string }>({});

  const validateForm = () => {
    const newErrors: typeof errors = {};
    if (!formData.to.trim()) newErrors.to = "Recipient email is required";
    else if (!formData.to.includes("@")) newErrors.to = "Invalid email format";
    if (!formData.subject.trim()) newErrors.subject = "Subject is required";
    if (!formData.body.trim()) newErrors.body = "Body is required";
    if (!formData.scheduled_date) newErrors.scheduled_date = "Schedule date is required";
    else {
      const scheduledDate = new Date(formData.scheduled_date);
      const now = new Date();
      if (scheduledDate <= now) {
        newErrors.scheduled_date = "Scheduled date must be in the future";
      }
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;

    setScheduleLoading(true);
    setScheduleResult(null);

    try {
      const res = await fetch(`${apiUrl}/api/scheduled-emails/schedule`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.detail || "Failed to schedule email");
      }

      setScheduleResult(`✓ Success: Email scheduled for ${new Date(data.scheduled_date).toLocaleString()}`);
      setFormData({ to: "", subject: "", body: "", scheduled_date: "" });
      onSuccess?.();
    } catch (err) {
      setScheduleResult(`✗ Error: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setScheduleLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (errors[name as keyof typeof errors]) {
      setErrors((prev) => ({ ...prev, [name]: undefined }));
    }
  };

  // Set default datetime-local value to tomorrow at 9am
  const defaultDate = new Date();
  defaultDate.setDate(defaultDate.getDate() + 1);
  defaultDate.setHours(9, 0, 0, 0);
  const defaultDateString = defaultDate.toISOString().slice(0, 16);

  return (
    <Card>
      <CardHeader title="Schedule Email" subtitle="Send an email at a future date and time" />
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            name="to"
            label="To"
            type="email"
            placeholder="recipient@example.com"
            value={formData.to}
            onChange={handleChange}
            error={errors.to}
            required
          />
          <Input
            name="subject"
            label="Subject"
            placeholder="Email subject"
            value={formData.subject}
            onChange={handleChange}
            error={errors.subject}
            required
          />
          <Textarea
            name="body"
            label="Body"
            placeholder="Email body content"
            value={formData.body}
            onChange={handleChange}
            error={errors.body}
            rows={4}
            required
          />
          <Input
            name="scheduled_date"
            label="Schedule Date & Time (UTC)"
            type="datetime-local"
            value={formData.scheduled_date || defaultDateString}
            onChange={handleChange}
            error={errors.scheduled_date}
            required
          />
        </form>
      </CardContent>
      <CardFooter>
        <Button type="submit" variant="warning" loading={scheduleLoading} disabled={scheduleLoading}>
          {scheduleLoading ? "Scheduling..." : "Schedule Email"}
        </Button>
        {scheduleResult && <p className="text-sm text-slate-700">{scheduleResult}</p>}
      </CardFooter>
    </Card>
  );
}