"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export default function ReportForm() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [locating, setLocating] = useState(false);
  const [error, setError] = useState("");
  const [locationError, setLocationError] = useState("");
  const [success, setSuccess] = useState("");
  const [latitude, setLatitude] = useState("");
  const [longitude, setLongitude] = useState("");

  function useMyLocation() {
    setLocationError("");
    setSuccess("");
    if (!navigator.geolocation) {
      setLocationError("Geolocation is not supported by this browser.");
      return;
    }

    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLatitude(position.coords.latitude.toFixed(6));
        setLongitude(position.coords.longitude.toFixed(6));
        setLocating(false);
      },
      (reason) => {
        setLocationError(
          reason.code === reason.PERMISSION_DENIED
            ? "Location permission was denied. Enter coordinates manually."
            : "Could not get location. Enter coordinates manually.",
        );
        setLocating(false);
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 },
    );
  }

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formEl = e.currentTarget;
    const form = new FormData(formEl);
    setLoading(true);
    setError("");
    setSuccess("");

    try {
      const res = await fetch("/api/public/reports/analyze", {
        method: "POST",
        body: form,
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        setError(body?.detail || `Report submission failed (HTTP ${res.status}).`);
        return;
      }

      const body = await res.json();
      formEl.reset();
      setLatitude("");
      setLongitude("");
      setSuccess(`Report submitted: ${body.report_id}`);
      router.refresh();
    } catch {
      setError("Could not connect to the CityMind API.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={submit} className="mt-8 rounded-xl border border-slate-800 bg-slate-900 p-4 md:p-5">
      <h2 className="text-xl font-semibold">Submit citizen report</h2>
      <p className="mt-1 text-sm text-slate-500">Add clear facts. AI output will require officer review.</p>

      <label className="mt-4 grid gap-1 text-sm text-slate-300">
        Description
        <textarea name="description" required maxLength={3000} rows={4} placeholder="Describe the issue, location, and visible risk..." className="rounded-lg border border-slate-700 bg-slate-950 p-3 text-base text-slate-100" />
      </label>

      <label className="mt-4 grid gap-1 text-sm text-slate-300">
        Evidence image (optional)
        <input name="image" type="file" accept="image/jpeg,image/png,image/webp" capture="environment" className="min-h-11 w-full rounded-lg border border-slate-700 bg-slate-950 p-2 text-slate-300" />
      </label>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm font-semibold text-slate-300">Location</p>
        <button type="button" onClick={useMyLocation} disabled={locating || loading} className="min-h-11 w-full rounded-lg border border-blue-700 px-4 text-sm font-semibold text-blue-300 hover:bg-blue-950 disabled:opacity-50 sm:w-auto">
          {locating ? "Getting location..." : "Use my location"}
        </button>
      </div>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <label className="grid gap-1 text-sm text-slate-400">
          Latitude
          <input name="latitude" type="number" inputMode="decimal" min="-90" max="90" step="any" value={latitude} onChange={(e) => setLatitude(e.target.value)} placeholder="21.028500" className="min-h-11 rounded-lg border border-slate-700 bg-slate-950 px-3 text-base text-slate-100" />
        </label>
        <label className="grid gap-1 text-sm text-slate-400">
          Longitude
          <input name="longitude" type="number" inputMode="decimal" min="-180" max="180" step="any" value={longitude} onChange={(e) => setLongitude(e.target.value)} placeholder="105.854200" className="min-h-11 rounded-lg border border-slate-700 bg-slate-950 px-3 text-base text-slate-100" />
        </label>
      </div>

      {locationError && <p role="alert" className="mt-3 text-sm text-amber-300">{locationError}</p>}
      {error && <p role="alert" className="mt-3 text-sm text-red-300">{error}</p>}
      {success && <p role="status" className="mt-3 break-all text-sm text-emerald-300">{success}</p>}

      <button type="submit" disabled={loading} className="mt-4 min-h-11 w-full rounded-lg bg-blue-600 px-5 font-semibold hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto">
        {loading ? "Analyzing..." : "Submit report"}
      </button>
    </form>
  );
}
