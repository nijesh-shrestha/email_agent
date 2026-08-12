import LoginButton from "@/components/loginButton";

export default function LoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center">
      <div className="space-y-4 text-center">
        <h1 className="text-3xl font-bold">
          AI Email Agent
        </h1>

        <p>
          Sign in with Google to continue.
        </p>

        <LoginButton />
      </div>
    </main>
  );
}