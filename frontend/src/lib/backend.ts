import "server-only";


function backendUrl() {
  return (
    process.env.BACKEND_API_URL ??
    process.env.NEXT_PUBLIC_API_URL ??
    "http://127.0.0.1:8000"
  ).replace(/\/$/, "");
}

export function backendEndpoint(path: string) {
  return `${backendUrl()}${path}`;
}

export function officerFetch(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  const key = process.env.OFFICER_API_KEY;
  if (key) headers.set("X-CityMind-Officer-Key", key);
  return fetch(backendEndpoint(path), { ...init, headers });
}
