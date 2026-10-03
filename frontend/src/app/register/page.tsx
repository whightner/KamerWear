import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { AuthCard } from "@/components/auth/AuthCard";
import { RegisterForm } from "@/components/auth/RegisterForm";
import { safeNextPath } from "@/lib/auth/cookies";
import { getCurrentUser } from "@/lib/auth/session";

export const metadata: Metadata = { title: "Create an account — KamerWear" };

export default async function RegisterPage({ searchParams }: PageProps<"/register">) {
  const { next } = await searchParams;
  const destination = safeNextPath(next);
  if (await getCurrentUser()) redirect(destination);

  return (
    <AuthCard
      title="Create an account"
      subtitle="Save your details for a faster checkout later."
    >
      <RegisterForm next={destination} />
    </AuthCard>
  );
}
