import "server-only";

import { call } from "@/lib/api/server";

export type { ApiFailure, ApiResult } from "@/lib/api/server";

// Server-side calls to the FastAPI auth/account endpoints. Only used by Server
// Actions, the proxy and Server Components: tokens never reach browser JS.

export interface Profile {
  first_name: string;
  last_name: string;
  phone: string | null;
  avatar_path: string | null;
}

export interface User {
  id: number;
  email: string;
  role: "customer" | "admin";
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  profile: Profile;
}

export interface AuthTokens {
  user: User;
  access_token: string;
  refresh_token: string;
  access_token_expires_in: number;
  refresh_token_expires_in: number;
}

export const authApi = {
  login: (email: string, password: string, clientIp: string | null) =>
    call<AuthTokens>("/auth/login", {
      method: "POST",
      body: { email, password },
      clientIp,
    }),
  register: (
    data: {
      email: string;
      password: string;
      first_name: string;
      last_name: string;
      phone: string | null;
    },
    clientIp: string | null,
  ) => call<AuthTokens>("/auth/register", { method: "POST", body: data, clientIp }),
  refresh: (refreshToken: string) =>
    call<AuthTokens>("/auth/refresh", {
      method: "POST",
      body: { refresh_token: refreshToken },
    }),
  logout: (refreshToken: string) =>
    call<void>("/auth/logout", {
      method: "POST",
      body: { refresh_token: refreshToken },
    }),
  me: (accessToken: string) => call<User>("/users/me", { accessToken }),
  updateMe: (
    accessToken: string,
    data: { first_name: string; last_name: string; phone: string | null },
  ) => call<User>("/users/me", { method: "PATCH", body: data, accessToken }),
  changePassword: (
    accessToken: string,
    data: { current_password: string; new_password: string },
  ) =>
    call<void>("/users/me/change-password", {
      method: "POST",
      body: data,
      accessToken,
    }),
};
