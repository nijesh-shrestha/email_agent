import { auth } from "@/auth";
import { redirect } from "next/navigation";
import LogoutButton from "@/components/logoutButton";

export default async function Dashboard() {
  const session = await auth();

  if (!session) {
    redirect("/login");
  }

  return (
    <main className="p-10">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-3xl font-bold">
            Dashboard
        </h1>

        <LogoutButton/>
      </div>

      <p>
        Welcome {session.user?.name}
      </p>

      <p>
        {session.user?.email}
      </p>
    </main>
  );
}