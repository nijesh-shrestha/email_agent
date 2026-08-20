"use client";

import React, { useState } from "react";
import { Card, CardHeader, CardContent, CardFooter, Button, Input, Textarea } from "@/components/ui";

interface SendEmailFormProps {
  apiUrl: string;
  token: string;
  onSuccess?: () => void;
}

export function SendEmailForm({ apiUrl, token, onSuccess }: SendEmailFormProps) {
  const [sending, setSending] = useState(false);
  const [sendResult, setSendResult] = useState<string | null>(null);
  const [formData, setFormData] = useState({ to: "", subject: "", body: "" });
  const [errors, setErrors] = useState<{ to?: string; subject?: string; body?: string }>({});

  const validateForm = () => {
    const newErrors: typeof errors = {};
    if (!formData.to.trim()) newErrors.to = "Recipient email is required";
    else if (!formData.to.includes("@")) newErrors.to = "Invalid email format";
    if (!formData.subject.trim()) newErrors.subject = "Subject is required";
    if (!formData.body.trim()) newErrors.body = "Body is required";
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;

    setSending(true);
    setSendResult(null);

    try {
      const res = await fetch(`${apiUrl}/api/gmail/send`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.detail ? JSON.stringify(data.detail) : "Failed to send email");
      }

      setSendResult(`✓ Sent: ${data.message_id || "Success"}`);
      setFormData({ to: "", subject: "", body: "" });
      onSuccess?.();
    } catch (err) {
      setSendResult(`✗ Error: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setSending(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (errors[name as keyof typeof errors]) {
      setErrors((prev) => ({ ...prev, [name]: undefined }));
    }
  };

  return (
    <Card>
      <CardHeader title="Send Test Email" />
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
            rows={6}
            required
          />
        </form>
      </CardContent>
      <CardFooter>
        <Button type="submit" variant="primary" loading={sending} disabled={sending}>
          {sending ? "Sending..." : "Send Email"}
        </Button>
        {sendResult && <p className="text-sm text-slate-700">{sendResult}</p>}
      </CardFooter>
    </Card>
  );
}