"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import LogoutButton from "@/components/logoutButton";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

type UserProfile = {
  id: number;
  email: string;
  name: string;
  image?: string | null;
};

export default function Dashboard() {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const token = window.localStorage.getItem("email_agent_token");
    if (!token) {
      router.replace("/login");
      return;
    }

    fetch(`${API_URL}/api/auth/me`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error("Unauthorized");
        }
        return response.json();
      })
      .then((data) => setUser(data))
      .catch(() => {
        window.localStorage.removeItem("email_agent_token");
        router.replace("/login");
      })
      .finally(() => setLoading(false));
  }, [router]);

  if (loading) {
    return <main className="flex min-h-screen items-center justify-center">Loading...</main>;
  }

  if (!user) {
    return null;
  }

  return (
    <main className="min-h-screen bg-slate-50 p-8">
      <div className="mx-auto flex max-w-4xl items-center justify-between rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.3em] text-slate-500">
            Dashboard
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900">
            Welcome back, {user.name}
          </h1>
          <p className="mt-2 text-slate-600">{user.email}</p>
        </div>

        <LogoutButton />
      </div>
    </main>
  );
}