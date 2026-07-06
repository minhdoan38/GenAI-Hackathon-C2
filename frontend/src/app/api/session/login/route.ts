import { NextResponse } from "next/server";

import {
  SESSION_COOKIE,
  authenticate,
  createSessionToken,
  sessionCookieOptions,
} from "@/lib/auth";

export async function POST(request: Request) {
  const form = await request.formData();
  const password = String(form.get("password") ?? "");
  const role = authenticate(password);
  if (!role) {
    return new NextResponse(null, {
      status: 303,
      headers: { Location: "/login?error=1" },
    });
  }

  const response = new NextResponse(null, {
    status: 303,
    headers: { Location: "/" },
  });
  response.cookies.set(SESSION_COOKIE, createSessionToken(role), sessionCookieOptions);
  return response;
}
