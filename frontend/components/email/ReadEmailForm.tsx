"use client";

import React, { useState } from "react";
import { Card, CardHeader, CardContent, CardFooter, Button, Input } from "@/components/ui";

interface ReadEmailFormProps {
  apiUrl: string;
  token: string;
}

export function ReadEmailForm({ apiUrl, token }: ReadEmailFormProps) {
  const [readLoading, setReadLoading] = useState(false);
  const [readResult, setReadResult] = useState<string | null>(null);
  const [formData, setFormData] = useState({ of_user: "", dates: "", amount: "" });
  const [errors, setErrors] = useState<{ of_user?: string }>({});

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.of_user.trim()) {
      setErrors({ of_user: "Please provide the sender email or name" });
      return;
    }

    setErrors({});
    setReadResult(null);
    setReadLoading(true);

    try {
      // Parse dates - optional
      const dates = formData.dates
        .split(",")
        .map((d) => d.trim())
        .filter(Boolean);

      // Parse amount - optional
      const amount = formData.amount ? Number(formData.amount) : undefined;

      // Build request body
      const requestBody: { of_user: string; dates?: string[]; amount?: number } = {
        of_user: formData.of_user
      };
      if (dates.length > 0) requestBody.dates = dates;
      if (amount !== undefined) requestBody.amount = amount;

      const res = await fetch(`${apiUrl}/api/gmail/read`, {
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
      const amountDisplay = amount ? ` (limit ${amount})` : " (latest by default)";

      setReadResult(
        `Found ${emailCount} email${emailCount === 1 ? "" : "s"} from ${formData.of_user}${dateInfo}${amountDisplay}.\n` +
          (emailList.length ? JSON.stringify(emailList.slice(0, 5), null, 2) : "No matching emails found.")
      );
    } catch (err) {
      setReadResult(`Error: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setReadLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (errors[name as keyof typeof errors]) {
      setErrors((prev) => ({ ...prev, [name]: undefined }));
    }
  };

  return (
    <Card>
      <CardHeader title="Read Gmail" subtitle="Search emails from a specific sender" />
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            name="of_user"
            label="Email or name of sender *"
            placeholder="sender@example.com or John Doe"
            value={formData.of_user}
            onChange={handleChange}
            error={errors.of_user}
            required
          />
          <Input
            name="dates"
            label="Dates (optional)"
            placeholder="2026-08-01, 2026-08-03 (leave empty for all emails)"
            value={formData.dates}
            onChange={handleChange}
            helperText="Comma-separated list of dates in YYYY-MM-DD format"
          />
          <Input
            name="amount"
            label="Amount (optional)"
            type="number"
            min={1}
            max={50}
            placeholder="5 (defaults to 1 - latest result)"
            value={formData.amount}
            onChange={handleChange}
          />
        </form>
      </CardContent>
      <CardFooter>
        <Button type="submit" variant="success" loading={readLoading} disabled={readLoading}>
          {readLoading ? "Reading..." : "Read Emails"}
        </Button>
      </CardFooter>
      {readResult && (
        <CardContent>
          <pre className="mt-3 max-h-80 overflow-auto rounded-md bg-slate-100 p-3 text-xs text-slate-800 whitespace-pre-wrap">
            {readResult}
          </pre>
        </CardContent>
      )}
    </Card>
  );
}