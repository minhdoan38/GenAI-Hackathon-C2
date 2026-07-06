import Link from "next/link";

import StatusActions from "@/components/StatusActions";
import { requireOfficerSession } from "@/lib/auth";
import { officerFetch } from "@/lib/backend";

type Props = { params: Promise<{ reportId: string }> };

type Report = {
  report_id: string;
  created_at: string;
  description?: string;
  latitude?: number | null;
  longitude?: number | null;
  category: string;
  severity: number;
  confidence: number;
  summary: string;
  recommendation: string;
  priority: string;
  estimated_impact?: string;
  evidence?: string[];
  uncertainty?: string[];
  urban_context?: string | Record<string, unknown> | null;
  image_gcs_uri?: string | null;
  status?: string;
  status_note?: string | null;
};

type StatusEvent = {
  status: string;
  note?: string | null;
  created_at: string;
};

type FetchResult<T> =
  | { data: T; error: null; notFound?: false }
  | { data: null; error: string; notFound?: boolean };

async function getReport(reportId: string): Promise<FetchResult<Report>> {
  try {
    const res = await officerFetch(`/api/v1/reports/${reportId}`, {
      cache: "no-store",
    });
    if (res.status === 404) {
      return { data: null, error: "Report not found.", notFound: true };
    }
    if (!res.ok) {
      return { data: null, error: `Could not load report (HTTP ${res.status}).` };
    }
    return { data: await res.json(), error: null };
  } catch {
    return { data: null, error: "Could not connect to the CityMind API." };
  }
}

async function getHistory(reportId: string): Promise<FetchResult<StatusEvent[]>> {
  try {
    const res = await officerFetch(
      `/api/v1/reports/${reportId}/status-history`,
      { cache: "no-store" },
    );
    if (!res.ok) {
      return {
        data: null,
        error: `Could not load status history (HTTP ${res.status}).`,
      };
    }
    const body = await res.json();
    return { data: body.items ?? [], error: null };
  } catch {
    return { data: null, error: "Could not connect to the history service." };
  }
}

function parseUrbanContext(
  value: Report["urban_context"],
): Record<string, unknown> | null {
  if (!value) return null;
  if (typeof value === "object") return value;
  try {
    const parsed: unknown = JSON.parse(value);
    return parsed && typeof parsed === "object"
      ? (parsed as Record<string, unknown>)
      : null;
  } catch {
    return { context: value };
  }
}

function formatDate(value?: string | null) {
  if (!value) return "Not available";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("en-GB");
}

function SignalList({ items }: { items?: string[] }) {
  if (!items?.length) {
    return <p className="mt-2 text-sm text-slate-500">None recorded.</p>;
  }
  return (
    <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-300">
      {items.map((item) => <li key={item}>{item}</li>)}
    </ul>
  );
}

export default async function ReportDetail({ params }: Props) {
  await requireOfficerSession();
  const { reportId } = await params;
  const [reportResult, historyResult] = await Promise.all([
    getReport(reportId),
    getHistory(reportId),
  ]);

  if (!reportResult.data) {
    return (
      <main className="min-h-screen bg-slate-950 p-8 text-slate-100">
        <section className="mx-auto max-w-4xl rounded-xl border border-slate-800 bg-slate-900 p-6">
          <h1 className="text-xl font-semibold">
            {reportResult.notFound ? "Report not found" : "Report unavailable"}
          </h1>
          <p className="mt-2 text-slate-400">{reportResult.error}</p>
          <Link href="/" className="mt-5 inline-block text-blue-400">
            ← Back to dashboard
          </Link>
        </section>
      </main>
    );
  }

  const report = reportResult.data;
  const history = historyResult.data ?? [];
  const urbanContext = parseUrbanContext(report.urban_context);

  return (
    <main className="min-h-screen bg-slate-950 p-4 text-slate-100 md:p-8">
      <section className="mx-auto max-w-4xl">
        <Link href="/" className="text-blue-400 hover:text-blue-300">
          ← Back to dashboard
        </Link>

        <header className="mt-6 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold capitalize">
              {report.category || "Uncategorized report"}
            </h1>
            <p className="mt-2 break-all text-sm text-slate-400">{report.report_id}</p>
            <p className="mt-1 text-sm text-slate-500">
              Submitted {formatDate(report.created_at)}
            </p>
          </div>
          <span className="rounded-full bg-blue-950 px-4 py-2 text-sm font-semibold text-blue-200">
            Status: {report.status ?? "new"}
          </span>
        </header>

        <div className="mt-6 rounded-xl border border-amber-800/60 bg-amber-950/30 p-4 text-sm text-amber-100">
          AI-generated analysis is advisory. An officer remains responsible for
          verification and the final decision.
        </div>

        <article className="mt-6 rounded-xl border border-slate-800 bg-slate-900 p-5">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              ["Priority", report.priority],
              ["Severity", `${report.severity}/5`],
              ["Confidence", `${Math.round(report.confidence * 100)}%`],
              ["Impact", report.estimated_impact || "Not available"],
            ].map(([label, value]) => (
              <div key={label}>
                <p className="text-xs uppercase text-slate-500">{label}</p>
                <p className="mt-1 font-semibold capitalize">{value}</p>
              </div>
            ))}
          </div>

          {report.description && (
            <section className="mt-6 border-t border-slate-800 pt-5">
              <h2 className="font-semibold">Citizen report</h2>
              <p className="mt-2 whitespace-pre-wrap text-slate-300">{report.description}</p>
            </section>
          )}

          <section className="mt-6 border-t border-slate-800 pt-5">
            <h2 className="font-semibold">AI summary</h2>
            <p className="mt-2 text-slate-300">{report.summary}</p>
          </section>

          <section className="mt-6 border-t border-slate-800 pt-5">
            <h2 className="font-semibold">Recommended action</h2>
            <p className="mt-2 text-slate-300">{report.recommendation}</p>
          </section>

          <div className="mt-6 grid gap-6 border-t border-slate-800 pt-5 md:grid-cols-2">
            <section>
              <h2 className="font-semibold">Evidence signals</h2>
              <SignalList items={report.evidence} />
            </section>
            <section>
              <h2 className="font-semibold">Uncertainty</h2>
              <SignalList items={report.uncertainty} />
            </section>
          </div>

          {(report.latitude != null || report.longitude != null) && (
            <section className="mt-6 border-t border-slate-800 pt-5">
              <h2 className="font-semibold">Reported location</h2>
              <p className="mt-2 text-sm text-slate-300">
                Latitude: {report.latitude ?? "not provided"} · Longitude:{" "}
                {report.longitude ?? "not provided"}
              </p>
            </section>
          )}

          {report.image_gcs_uri && (
            <section className="mt-6 border-t border-slate-800 pt-5">
              <h2 className="mb-3 font-semibold">Evidence image</h2>
              {/* Private evidence is intentionally served by the API proxy. */}
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={`/api/officer/reports/${report.report_id}/image`}
                alt="Citizen-provided report evidence"
                className="max-h-96 rounded-lg border border-slate-800 object-contain"
              />
            </section>
          )}

          <section className="mt-6 border-t border-slate-800 pt-5">
            <h2 className="font-semibold">Officer action</h2>
            {report.status_note && (
              <p className="mt-2 text-sm text-slate-400">
                Latest note: {report.status_note}
              </p>
            )}
            <StatusActions reportId={report.report_id} currentStatus={report.status} />
          </section>
        </article>

        <section className="mt-6 rounded-xl border border-slate-800 bg-slate-900 p-5">
          <h2 className="text-xl font-semibold">Urban context</h2>
          <p className="mt-1 text-sm text-slate-500">
            Supporting context only; it is not a prediction or verified incident fact.
          </p>
          {urbanContext && Object.keys(urbanContext).length > 0 ? (
            <pre className="mt-4 overflow-x-auto whitespace-pre-wrap rounded-lg bg-slate-950 p-4 text-sm text-slate-300">
              {JSON.stringify(urbanContext, null, 2)}
            </pre>
          ) : (
            <p className="mt-4 text-sm text-slate-500">
              No urban context was recorded for this report.
            </p>
          )}
        </section>

        <section className="mt-6 rounded-xl border border-slate-800 bg-slate-900 p-5">
          <h2 className="text-xl font-semibold">Status history</h2>
          {historyResult.error && (
            <p className="mt-3 rounded-lg border border-red-900 bg-red-950/40 p-3 text-sm text-red-200">
              {historyResult.error}
            </p>
          )}
          {!historyResult.error && history.length === 0 && (
            <p className="mt-3 text-sm text-slate-500">
              No status changes yet. This report is currently new.
            </p>
          )}
          <ol className="mt-3 grid gap-3">
            {history.map((item) => (
              <li
                key={`${item.status}-${item.created_at}`}
                className="rounded-lg border border-slate-800 bg-slate-950 p-4"
              >
                <p className="font-semibold capitalize">{item.status}</p>
                <p className="text-sm text-slate-400">{formatDate(item.created_at)}</p>
                {item.note && <p className="mt-2 text-slate-300">{item.note}</p>}
              </li>
            ))}
          </ol>
        </section>
      </section>
    </main>
  );
}
