"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Card, CardHeader, CardContent, Button, Input, Textarea, Select } from "@/components/ui";
import { formatNptDateTime, nptInputToUtc, toNptDateTimeInput } from "@/lib/timezone";

interface CreateTaskFormProps {
  apiUrl: string;
  token: string;
  onSuccess?: () => void;
}

interface TaskList {
  id: string;
  title: string;
}

export function CreateTaskForm({ apiUrl, token, onSuccess }: CreateTaskFormProps) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [taskLists, setTaskLists] = useState<TaskList[]>([]);
  const [formData, setFormData] = useState({
    title: "",
    notes: "",
    due_datetime: "",
    task_list_id: "@default",
  });
  const [errors, setErrors] = useState<{ title?: string; due_datetime?: string }>({});

  const fetchTaskLists = useCallback(async () => {
    try {
      const res = await fetch(`${apiUrl}/api/calendar/task-lists`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (res.ok && data.task_lists) {
        setTaskLists(data.task_lists);
      }
    } catch {
      // Ignore errors, keep default
    }
  }, [apiUrl, token]);

  useEffect(() => {
    fetchTaskLists();
  }, [fetchTaskLists]);

  const validateForm = () => {
    const newErrors: typeof errors = {};
    if (!formData.title.trim()) newErrors.title = "Task title is required";
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!validateForm()) return;

    setLoading(true);
    setResult(null);

    try {
      let dueUtc = formData.due_datetime;
      if (dueUtc) {
        dueUtc = nptInputToUtc(dueUtc);
      }

      const res = await fetch(`${apiUrl}/api/calendar/tasks`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title: formData.title,
          notes: formData.notes,
          due_datetime: dueUtc || undefined,
          task_list_id: formData.task_list_id,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.detail || "Failed to create task");
      }

      setResult(`✓ Success: Task "${data.task?.title}" created${data.task?.due ? ` due ${formatNptDateTime(data.task.due)} NPT` : ""}`);
      setFormData({ title: "", notes: "", due_datetime: "", task_list_id: "@default" });
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

  // Set default datetime-local value to tomorrow at 9am
  const defaultDue = new Date();
  defaultDue.setDate(defaultDue.getDate() + 1);
  defaultDue.setHours(9, 0, 0, 0);
  const defaultDueString = toNptDateTimeInput(defaultDue);

  return (
    <Card>
      <CardHeader title="Create Task" subtitle="Add a new task to your Google Tasks" />
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            name="title"
            label="Task Title"
            placeholder="Buy groceries, Finish report, Call client..."
            value={formData.title}
            onChange={handleChange}
            error={errors.title}
            required
          />
          <Textarea
            name="notes"
            label="Notes (optional)"
            placeholder="Additional details, steps, context..."
            value={formData.notes}
            onChange={handleChange}
            rows={3}
          />
          <Input
            name="due_datetime"
            label="Due Date & Time (NPT, optional)"
            type="datetime-local"
            value={formData.due_datetime || defaultDueString}
            onChange={handleChange}
            error={errors.due_datetime}
          />
          <Select
            name="task_list_id"
            label="Task List"
            value={formData.task_list_id}
            onChange={handleChange}
            options={taskLists.length > 0
              ? taskLists.map((list) => ({ value: list.id, label: list.title }))
              : [{ value: "@default", label: "Default Task List" }]}
          />
          <div className="flex items-center gap-3 pt-2">
            <Button type="submit" variant="warning" loading={loading} disabled={loading}>
              {loading ? "Creating..." : "Create Task"}
            </Button>
            {result && <p className="text-sm text-slate-700">{result}</p>}
          </div>
        </form>
      </CardContent>
    </Card>
  );
}