"use client";

import { signIn } from "next-auth/react";

export default function LoginButton() {
  return (
    <button
      onClick={() => signIn("google", { callbackUrl: "/dashboard" })}
      className="px-4 py-2 rounded bg-blue-600 text-white"
    >
      Continue with Google
    </button>
  );
}