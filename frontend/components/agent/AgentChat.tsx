"use client";

import React, { useState, useEffect } from "react";
import { Card, CardHeader, CardContent, CardFooter, Button, Textarea, Input } from "@/components/ui";

interface AgentMessage {
  role: "user" | "model" | "tool";
  text: string;
}

interface AgentEventPart {
  text: string | null;
  thought: boolean | null;
  function_call: any;
  function_response: any;
  tool_call: any;
  tool_response: any;
  part_metadata: any;
}

interface AgentEvent {
  author: string | null;
  invocation_id: string | null;
  partial: boolean;
  content: AgentEventPart[];
}

interface AgentChatProps {
  apiUrl: string;
  token: string;
  endpoint: string; // e.g., "/api/agent/run" or "/api/calendar/run"
  title: string;
  subtitle?: string;
  placeholder?: string;
  initialPrompt?: string;
}

export function AgentChat({
  apiUrl,
  token,
  endpoint,
  title,
  subtitle,
  placeholder = "Ask the agent...",
  initialPrompt,
}: AgentChatProps) {
  const [agentPrompt, setAgentPrompt] = useState(initialPrompt || "");
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
      const res = await fetch(`${apiUrl}${endpoint}`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: prompt, session_id: agentSessionId }),
      });

      if (!res.ok) {
        const errText = await res.text();
        throw new Error(errText || "Agent request failed");
      }

      const data = await res.json();
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

  // Handle initial prompt if provided
  useEffect(() => {
    if (initialPrompt && agentMessages.length === 0 && !agentLoading) {
      // Auto-submit the initial prompt
      const form = document.createElement("form");
      form.dispatchEvent(new Event("submit"));
    }
  }, [initialPrompt, agentMessages.length, agentLoading]);

  return (
    <Card className="lg:col-span-2">
      <CardHeader title={title} subtitle={subtitle} />
      <CardContent>
        <form onSubmit={sendAgentMessage} className="space-y-4">
          <Textarea
            label="Your message"
            placeholder={placeholder}
            value={agentPrompt}
            onChange={(e) => setAgentPrompt(e.target.value)}
            rows={5}
            required
          />
        </form>
      </CardContent>
      <CardFooter>
        <Button type="submit" form="agent-form" variant="primary" loading={agentLoading} disabled={agentLoading || !agentPrompt.trim()}>
          {agentLoading ? "Thinking..." : "Send to Agent"}
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