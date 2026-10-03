import type { Metadata } from "next";
import { Breadcrumbs } from "@/components/catalog/Breadcrumbs";
import { ChangePasswordForm } from "@/components/auth/ChangePasswordForm";
import { ProfileForm } from "@/components/auth/ProfileForm";
import { Container } from "@/components/storefront/Container";
import { requireUser } from "@/lib/auth/session";

export const metadata: Metadata = { title: "Profile — KamerWear" };

export default async function ProfilePage() {
  const user = await requireUser("/account/profile");
  const { first_name, last_name, phone } = user.profile;

  return (
    <Container className="pb-16 pt-6">
      <Breadcrumbs
        items={[
          { label: "Home", href: "/" },
          { label: "My account", href: "/account" },
          { label: "Profile" },
        ]}
      />
      <h1 className="mt-4 text-3xl font-extrabold tracking-tight text-ink">Profile</h1>
      <p className="mt-1 text-sm text-muted">Update your personal details and password.</p>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <section
          aria-labelledby="personal-details"
          className="rounded-xl border border-line bg-white p-5 sm:p-6"
        >
          <h2 id="personal-details" className="mb-5 text-lg font-bold text-ink">
            Personal details
          </h2>
          <ProfileForm
            email={user.email}
            firstName={first_name}
            lastName={last_name}
            phone={phone ?? ""}
          />
        </section>
        <section
          aria-labelledby="change-password"
          className="rounded-xl border border-line bg-white p-5 sm:p-6"
        >
          <h2 id="change-password" className="mb-5 text-lg font-bold text-ink">
            Change password
          </h2>
          <ChangePasswordForm />
        </section>
      </div>
    </Container>
  );
}
