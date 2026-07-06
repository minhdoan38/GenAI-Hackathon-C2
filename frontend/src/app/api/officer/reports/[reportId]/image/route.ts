import { getSession } from "@/lib/auth";
import { officerFetch } from "@/lib/backend";

type Context = { params: Promise<{ reportId: string }> };

export async function GET(_request: Request, { params }: Context) {
  if (!(await getSession())) return Response.json({ detail: "Unauthorized" }, { status: 401 });
  const { reportId } = await params;
  const response = await officerFetch(
    `/api/v1/reports/${encodeURIComponent(reportId)}/image`,
  );
  return new Response(response.body, {
    status: response.status,
    headers: {
      "Content-Type": response.headers.get("Content-Type") ?? "application/octet-stream",
      "Cache-Control": "private, max-age=60",
    },
  });
}
