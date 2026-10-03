import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { AuthCard } from "@/components/auth/AuthCard";
import { LoginForm } from "@/components/auth/LoginForm";
import { safeNextPath } from "@/lib/auth/cookies";
import { getCurrentUser } from "@/lib/auth/session";

export const metadata: Metadata = { title: "Log in — KamerWear" };

export default async function LoginPage({ searchParams }: PageProps<"/login">) {
  const { next, reason } = await searchParams;
  const destination = safeNextPath(next);
  if (await getCurrentUser()) redirect(destination);

  return (
    <AuthCard title="Log in" subtitle="Welcome back to KamerWear.">
      <LoginForm
        next={destination}
        notice={
          reason === "expired"
            ? "Your session has expired. Please log in again."
            : undefined
        }
      />
    </AuthCard>
  );
}
