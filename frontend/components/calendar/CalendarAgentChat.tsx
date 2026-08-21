"use client";

import React, { useState } from "react";
import { Card, CardHeader, CardContent, CardFooter, Button, Textarea } from "@/components/ui";

interface AgentMessage {
  role: "user" | "model" | "tool";
  text: string;
}

interface AgentEventPart {
  text?: string | null;
  thought?: boolean | null;
  function_call?: Record<string, unknown> | null;
  function_response?: Record<string, unknown> | null;
  tool_call?: Record<string, unknown> | null;
  tool_response?: Record<string, unknown> | null;
  part_metadata?: Record<string, unknown> | null;
}

interface AgentEvent {
  author: string | null;
  invocation_id: string | null;
  partial: boolean;
  content: AgentEventPart[];
}

interface CalendarRunResponse {
  session_id: string | null;
  events?: AgentEvent[];
}

interface CalendarAgentChatProps {
  apiUrl: string;
  token: string;
}

export function CalendarAgentChat({ apiUrl, token }: CalendarAgentChatProps) {
  const [agentPrompt, setAgentPrompt] = useState("");
  const [agentMessages, setAgentMessages] = useState<AgentMessage[]>([]);
  const [agentSessionId, setAgentSessionId] = useState<string | null>(null);
  const [agentLoading, setAgentLoading] = useState(false);
  const [agentError, setAgentError] = useState<string | null>(null);

  const sendAgentMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    const prompt = agentPrompt.trim();
    if (!prompt) return;

    const userMessage: AgentMessage = { role: "user", text: prompt };
    setAgentPrompt("");
    setAgentError(null);
    setAgentLoading(true);

    try {
      const res = await fetch(`${apiUrl}/api/calendar/run`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: prompt, session_id: agentSessionId }),
      });

      if (!res.ok) {
        let errorMessage = "Calendar agent request failed";
        try {
          const errData = await res.json();
          errorMessage = errData.detail || errData.message || errorMessage;
        } catch {
          const errText = await res.text();
          errorMessage = errText || errorMessage;
        }

        // Handle insufficient calendar scope error specifically
        if (res.status === 403 && errorMessage.includes("Calendar access")) {
          errorMessage = "Google Calendar access requires additional permissions. Please reconnect your Google account to grant Calendar access.";
        }

        throw new Error(errorMessage);
      }

      const data: CalendarRunResponse = await res.json();
      setAgentSessionId(data.session_id);

      const nextMessages: AgentMessage[] = [];
      for (const event of data.events || []) {
        for (const part of event.content || []) {
          if (part.text) {
            const role: AgentMessage["role"] = event.author === "tool" ? "tool" : "model";
            nextMessages.push({
              role,
              text: part.text,
            });
          }
        }
      }

      setAgentMessages((current) => [...current, userMessage, ...nextMessages]);
    } catch (err) {
      setAgentError(err instanceof Error ? err.message : String(err));
    } finally {
      setAgentLoading(false);
    }
  };

  // Example prompts for the calendar agent
  const examplePrompts = [
    "What's on my calendar today?",
    "Show me events for tomorrow",
    "What are my upcoming events for the next 7 days?",
    "List all my calendars",
    "Show me events for 2026-08-20",
    "What meetings do I have this week?",
  ];

  const handleExamplePrompt = (prompt: string) => {
    setAgentPrompt(prompt);
  };

  return (
    <Card className="lg:col-span-2">
      <CardHeader
        title="Google Calendar Assistant"
        subtitle="Ask about your calendar events, upcoming meetings, and available calendars"
      />
      <CardContent>
        <form id="calendar-agent-form" onSubmit={sendAgentMessage} className="space-y-4">
          <Textarea
            label="Ask the calendar agent"
            placeholder="What's on my calendar today? / Show me upcoming events / List all calendars..."
            value={agentPrompt}
            onChange={(e) => setAgentPrompt(e.target.value)}
            rows={4}
            required
          />

          <div className="space-y-2">
            <p className="text-xs text-slate-500">Example prompts:</p>
            <div className="flex flex-wrap gap-2">
              {examplePrompts.map((prompt) => (
                <Button
                  key={prompt}
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => handleExamplePrompt(prompt)}
                  className="text-xs"
                >
                  {prompt}
                </Button>
              ))}
            </div>
          </div>
        </form>
      </CardContent>
      <CardFooter>
        <Button type="submit" form="calendar-agent-form" variant="primary" loading={agentLoading} disabled={agentLoading || !agentPrompt.trim()}>
          {agentLoading ? "Thinking..." : "Ask Calendar Agent"}
        </Button>
        {agentError && <p className="text-sm text-red-600">{agentError}</p>}
      </CardFooter>
      {agentSessionId && (
        <CardContent>
          <p className="mt-3 text-sm text-slate-500">Agent session id: {agentSessionId}</p>
        </CardContent>
      )}
      {agentMessages.length > 0 && (
        <CardContent>
          <div className="mt-4 space-y-3 max-h-96 overflow-auto">
            {agentMessages.map((message, index) => (
              <div
                key={`${index}-${message.role}`}
                className={`rounded-xl border px-4 py-3 ${
                  message.role === "user"
                    ? "border-slate-200 bg-slate-50"
                    : message.role === "tool"
                    ? "border-amber-200 bg-amber-50"
                    : "border-slate-200 bg-white"
                }`}
              >
                <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
                  {message.role}
                </p>
                <p className="mt-2 whitespace-pre-wrap text-sm text-slate-800">{message.text}</p>
              </div>
            ))}
          </div>
        </CardContent>
      )}
    </Card>
  );
}