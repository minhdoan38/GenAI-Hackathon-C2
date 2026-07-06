import { backendEndpoint } from "@/lib/backend";

export async function POST(request: Request) {
  const form = await request.formData();
  const response = await fetch(backendEndpoint("/api/v1/reports/analyze"), {
    method: "POST",
    body: form,
  });
  return new Response(response.body, {
    status: response.status,
    headers: { "Content-Type": response.headers.get("Content-Type") ?? "application/json" },
  });
}
