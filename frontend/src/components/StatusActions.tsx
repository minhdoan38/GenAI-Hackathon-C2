"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

type Props = {
  reportId: string;
  currentStatus?: string;
};

export default function StatusActions({ reportId, currentStatus }: Props) {
  const router = useRouter();
  const [loading, setLoading] = useState("");
  const [error, setError] = useState("");

  async function updateStatus(status: string) {
    setLoading(status);
    setError("");

    const url = new URL(
      `/api/officer/reports/${reportId}/status`,
      window.location.origin,
    );
    url.searchParams.set("status", status);

    try {
      const res = await fetch(url.toString(), { method: "PATCH" });
      if (!res.ok) {
        setError(`Status update failed (HTTP ${res.status}).`);
        return;
      }
      router.refresh();
    } catch {
      setError("Could not connect to the CityMind API.");
    } finally {
      setLoading("");
    }
  }

  return (
    <div className="mt-4">
      <div className="flex flex-wrap gap-2">
        {["reviewing", "resolved", "rejected"].map((status) => (
          <button
            type="button"
            key={status}
            onClick={() => updateStatus(status)}
            disabled={Boolean(loading) || currentStatus === status}
            className="rounded-lg bg-slate-800 px-3 py-2 text-sm capitalize hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading === status
              ? "Updating..."
              : currentStatus === status
                ? `${status} (current)`
                : status}
          </button>
        ))}
      </div>
      {error && (
        <p role="alert" className="mt-3 text-sm text-red-300">
          {error}
        </p>
      )}
    </div>
  );
}
