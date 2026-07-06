import { getSession } from "@/lib/auth";
import { officerFetch } from "@/lib/backend";

type Context = { params: Promise<{ reportId: string }> };

export async function PATCH(request: Request, { params }: Context) {
  if (!(await getSession())) return Response.json({ detail: "Unauthorized" }, { status: 401 });
  const { reportId } = await params;
  const incoming = new URL(request.url).searchParams;
  const query = new URLSearchParams();
  if (incoming.get("status")) query.set("status", incoming.get("status")!);
  if (incoming.get("note")) query.set("note", incoming.get("note")!);
  const response = await officerFetch(
    `/api/v1/reports/${encodeURIComponent(reportId)}/status?${query}`,
    { method: "PATCH" },
  );
  return new Response(response.body, {
    status: response.status,
    headers: { "Content-Type": response.headers.get("Content-Type") ?? "application/json" },
  });
}
