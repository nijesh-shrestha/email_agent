import AuthPanel from "@/components/authPanel";

export default function LoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12">
      <div className="w-full max-w-5xl rounded-3xl border border-slate-200 bg-white p-8 shadow-sm lg:flex lg:items-center lg:justify-between lg:gap-12">
        <div className="mb-8 max-w-lg lg:mb-0">
          <p className="text-sm font-semibold uppercase tracking-[0.3em] text-slate-500">
            Module 1 — Authentication
          </p>
          <h1 className="mt-3 text-4xl font-semibold tracking-tight text-slate-900">
            AI Email Agent
          </h1>
          <p className="mt-4 text-lg leading-8 text-slate-600">
            Create an account or log in to manage your own secure workspace.
          </p>
        </div>

        <AuthPanel />
      </div>
    </main>
  );
}