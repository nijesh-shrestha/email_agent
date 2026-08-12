"use client";

import { useRouter } from "next/navigation";

export default function LogoutButton() {
  const router = useRouter();

  return (
    <button
      onClick={() => {
        window.localStorage.removeItem("email_agent_token");
        router.push("/login");
      }}
      className="rounded bg-red-600 px-4 py-2 text-white"
    >
      Logout
    </button>
  );
}