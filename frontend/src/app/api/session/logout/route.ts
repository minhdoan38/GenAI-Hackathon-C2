import { NextResponse } from "next/server";

import { SESSION_COOKIE } from "@/lib/auth";

export async function POST() {
  const response = new NextResponse(null, {
    status: 303,
    headers: { Location: "/login" },
  });
  response.cookies.set(SESSION_COOKIE, "", { path: "/", maxAge: 0 });
  return response;
}
