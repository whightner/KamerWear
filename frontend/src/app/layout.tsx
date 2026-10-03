import type { Metadata } from "next";
import { Suspense } from "react";
import { Geist, Geist_Mono } from "next/font/google";
import { CartNotice } from "@/components/store/CartNotice";
import { StoreProvider } from "@/components/store/StoreProvider";
import { Footer } from "@/components/storefront/Footer";
import { Header } from "@/components/storefront/Header";
import { StorefrontOnly } from "@/components/storefront/StorefrontOnly";
import { getCurrentUser, getServerCart } from "@/lib/auth/session";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "KamerWear — Fashion for Cameroon",
  description:
    "Shop shoes, clothes, streetwear and accessories with flash deals, Smart Fit size recommendations and delivery across Cameroon.",
};

export default async function RootLayout({ children }: LayoutProps<"/">) {
  // Only the first name reaches the browser; tokens stay in HttpOnly cookies.
  const [user, serverCart] = await Promise.all([getCurrentUser(), getServerCart()]);

  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <StoreProvider signedIn={!!user} serverCart={user ? serverCart : null}>
          <StorefrontOnly>
            <Header
              account={
                user
                  ? { firstName: user.profile.first_name, isAdmin: user.role === "admin" }
                  : null
              }
            />
            <Suspense fallback={null}>
              <CartNotice />
            </Suspense>
          </StorefrontOnly>
          <main className="flex-1">{children}</main>
          <StorefrontOnly>
            <Footer />
          </StorefrontOnly>
        </StoreProvider>
      </body>
    </html>
  );
}
