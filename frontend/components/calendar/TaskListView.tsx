"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Card, CardHeader, CardContent, Button, Input, Select, Badge } from "@/components/ui";
import { formatNptDateTime } from "@/lib/timezone";

interface Task {
  id: string;
  title: string;
  notes: string;
  due: string;
  status: string;
  updated: string;
}

interface TaskListProps {
  apiUrl: string;
  token: string;
}

export function TaskListView({ apiUrl, token }: TaskListProps) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [taskLists, setTaskLists] = useState<{ id: string; title: string }[]>([]);
  const [selectedTaskList, setSelectedTaskList] = useState("@default");
  const [showCompleted, setShowCompleted] = useState(false);
  const [maxResults, setMaxResults] = useState(20);

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
      // Ignore errors
    }
  }, [apiUrl, token]);

  const fetchTasks = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      params.append("task_list_id", selectedTaskList);
      params.append("max_results", maxResults.toString());
      params.append("show_completed", showCompleted.toString());

      const res = await fetch(`${apiUrl}/api/calendar/tasks?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      const data = await res.json();
      if (!res.ok) {
        let errorMessage = data?.detail || "Failed to fetch tasks";

        if (res.status === 403 && errorMessage.includes("Tasks access")) {
          errorMessage = "Google Tasks access requires additional permissions. Please reconnect your Google account to grant Tasks access.";
        }

        throw new Error(errorMessage);
      }

      setTasks(data.tasks || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [apiUrl, token, selectedTaskList, maxResults, showCompleted]);

  useEffect(() => {
    fetchTaskLists();
  }, [fetchTaskLists]);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  // Listen for refresh events
  useEffect(() => {
    const handleRefresh = () => fetchTasks();
    window.addEventListener("tasks-refresh", handleRefresh);
    return () => window.removeEventListener("tasks-refresh", handleRefresh);
  }, [fetchTasks]);

  const handleTaskListChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedTaskList(e.target.value);
  };

  const handleShowCompletedChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setShowCompleted(e.target.checked);
  };

  const handleMaxResultsChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = Math.max(1, Math.min(100, Number(e.target.value) || 1));
    setMaxResults(value);
  };

  const handleRefresh = () => {
    setLoading(true);
    void fetchTasks();
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "completed":
        return <Badge variant="success">Completed</Badge>;
      case "needsAction":
        return <Badge variant="warning">Pending</Badge>;
      default:
        return <Badge variant="default">{status}</Badge>;
    }
  };

  return (
    <Card className="lg:col-span-2">
      <CardHeader
        title="Tasks"
        subtitle="View and manage your Google Tasks"
        action={
          <div className="flex flex-wrap items-center gap-2">
            <Select
              label="Task List"
              value={selectedTaskList}
              onChange={handleTaskListChange}
              options={taskLists.map((tl) => ({ value: tl.id, label: tl.title }))}
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
            <label className="flex items-center gap-1 text-sm text-slate-600">
              <input
                type="checkbox"
                checked={showCompleted}
                onChange={handleShowCompletedChange}
                className="rounded border-slate-300"
              />
              Show completed
            </label>
            <Button variant="secondary" size="sm" onClick={handleRefresh} disabled={loading}>
              {loading ? "Refreshing..." : "Refresh"}
            </Button>
          </div>
        }
      />
      <CardContent>
        {loading ? (
          <p className="text-sm text-slate-500 text-center py-4">Loading tasks...</p>
        ) : error ? (
          <div className="p-3 rounded-md bg-red-50 text-red-700 text-sm" role="alert">
            {error}
          </div>
        ) : tasks.length === 0 ? (
          <p className="text-sm text-slate-500 text-center py-4">No tasks found</p>
        ) : (
          <div className="space-y-2 max-h-96 overflow-auto">
            {tasks.map((task) => (
              <div
                key={task.id}
                className={`rounded-lg border p-4 hover:bg-slate-50 transition-colors ${
                  task.status === "completed" ? "border-slate-200 bg-green-50" : "border-slate-200 bg-white"
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className={`font-medium text-slate-900 truncate ${task.status === "completed" ? "line-through text-slate-500" : ""}`}>
                        {task.title || "(No title)"}
                      </p>
                      {getStatusBadge(task.status)}
                    </div>
                    {task.notes && (
                      <p className="text-sm text-slate-500 mt-1 line-clamp-2">{task.notes}</p>
                    )}
                    {task.due && (
                      <p className="text-sm text-slate-500 mt-1 flex items-center gap-1">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        Due: {formatNptDateTime(task.due)} NPT
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}