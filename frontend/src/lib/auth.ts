import "server-only";

import { createHmac, timingSafeEqual } from "node:crypto";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";


export const SESSION_COOKIE = "citymind_officer_session";
const SESSION_SECONDS = 8 * 60 * 60;

type Role = "officer" | "admin";
type Session = { role: Role; expiresAt: number };

function secret() {
  const value = process.env.SESSION_SECRET;
  if (value) return value;
  if (process.env.NODE_ENV !== "production") return "citymind-local-session-only";
  throw new Error("SESSION_SECRET is required in production");
}

function sign(payload: string) {
  return createHmac("sha256", secret()).update(payload).digest("base64url");
}

function equal(left: string, right: string) {
  const a = Buffer.from(left);
  const b = Buffer.from(right);
  return a.length === b.length && timingSafeEqual(a, b);
}

export function authenticate(password: string): Role | null {
  const officer = process.env.OFFICER_DASHBOARD_PASSWORD ?? (
    process.env.NODE_ENV !== "production" ? "citymind-demo" : ""
  );
  const admin = process.env.ADMIN_DASHBOARD_PASSWORD ?? "";
  if (admin && equal(password, admin)) return "admin";
  if (officer && equal(password, officer)) return "officer";
  return null;
}

export function createSessionToken(role: Role) {
  const payload = Buffer.from(
    JSON.stringify({ role, expiresAt: Date.now() + SESSION_SECONDS * 1000 }),
  ).toString("base64url");
  return `${payload}.${sign(payload)}`;
}

export function verifySessionToken(token?: string): Session | null {
  if (!token) return null;
  const [payload, signature, extra] = token.split(".");
  if (!payload || !signature || extra || !equal(signature, sign(payload))) return null;
  try {
    const session = JSON.parse(Buffer.from(payload, "base64url").toString()) as Session;
    if (!(["officer", "admin"] as string[]).includes(session.role)) return null;
    if (!Number.isFinite(session.expiresAt) || session.expiresAt <= Date.now()) return null;
    return session;
  } catch {
    return null;
  }
}

export async function getSession() {
  const store = await cookies();
  return verifySessionToken(store.get(SESSION_COOKIE)?.value);
}

export async function requireOfficerSession() {
  const session = await getSession();
  if (!session) redirect("/login");
  return session;
}

export const sessionCookieOptions = {
  httpOnly: true,
  secure: process.env.NODE_ENV === "production",
  sameSite: "strict" as const,
  path: "/",
  maxAge: SESSION_SECONDS,
};
