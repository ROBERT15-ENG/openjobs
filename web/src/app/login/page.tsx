import type { Metadata } from "next";
import LoginForm from "@/components/LoginForm";

export const metadata: Metadata = { title: "Log in" };

type SP = Record<string, string | string[] | undefined>;

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<SP>;
}) {
  const sp = await searchParams;
  const registered = (Array.isArray(sp.registered) ? sp.registered[0] : sp.registered) === "1";
  return (
    <div className="auth-wrap">
      <LoginForm justRegistered={registered} />
    </div>
  );
}
