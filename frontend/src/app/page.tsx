import Link from "next/link";

import StatusActions from "@/components/StatusActions";
import { requireOfficerSession } from "@/lib/auth";
import { officerFetch } from "@/lib/backend";

type Report = {
  report_id: string;
  created_at: string;
  description: string;
  category: string;
  severity: number;
  confidence: number;
  summary: string;
  recommendation: string;
  priority: string;
  estimated_impact: string;
  status: string;
  status_note?: string;
  image_gcs_uri?: string;
};

type Summary = {
  total_reports: number;
  critical_reports: number;
  avg_severity: number;
  top_category: string;
};

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

type Filters = {
  status: string;
  category: string;
  priority: string;
  minSeverity: string;
  maxSeverity: string;
};

type FetchResult<T> = { data: T; error: string | null };

const statuses = ["new", "reviewing", "resolved", "rejected"];
const categories = [
  "pothole",
  "flooding",
  "waste",
  "streetlight",
  "obstruction",
  "other",
];
const priorities = ["low", "medium", "high", "critical"];

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] ?? "" : value ?? "";
}

function readFilters(params: Record<string, string | string[] | undefined>): Filters {
  return {
    status: first(params.status),
    category: first(params.category),
    priority: first(params.priority),
    minSeverity: first(params.min_severity),
    maxSeverity: first(params.max_severity),
  };
}

async function getReports(filters: Filters): Promise<FetchResult<Report[]>> {
  const query = new URLSearchParams({ limit: "20" });
  if (filters.status) query.set("status", filters.status);
  if (filters.category) query.set("category", filters.category);
  if (filters.priority) query.set("priority", filters.priority);
  if (filters.minSeverity) query.set("min_severity", filters.minSeverity);
  if (filters.maxSeverity) query.set("max_severity", filters.maxSeverity);

  try {
    const res = await officerFetch(`/api/v1/reports/recent?${query}`, {
      cache: "no-store",
    });
    if (!res.ok) {
      return { data: [], error: `Could not load reports (HTTP ${res.status}).` };
    }
    const body = await res.json();
    return { data: body.items ?? [], error: null };
  } catch {
    return { data: [], error: "Could not connect to the CityMind API." };
  }
}

async function getSummary(): Promise<FetchResult<Summary>> {
  const fallback = {
    total_reports: 0,
    critical_reports: 0,
    avg_severity: 0,
    top_category: "none",
  };
  try {
    const res = await officerFetch("/api/v1/reports/summary", {
      cache: "no-store",
    });
    if (!res.ok) {
      return { data: fallback, error: `Summary unavailable (HTTP ${res.status}).` };
    }
    return { data: await res.json(), error: null };
  } catch {
    return { data: fallback, error: "Summary service is unavailable." };
  }
}

function FilterSelect({
  name,
  label,
  value,
  options,
}: {
  name: string;
  label: string;
  value: string;
  options: string[];
}) {
  return (
    <label className="grid gap-1 text-sm text-slate-300">
      {label}
      <select
        name={name}
        defaultValue={value}
        className="min-h-11 rounded-lg border border-slate-700 bg-slate-950 px-3 text-slate-100"
      >
        <option value="">All</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

export default async function Home({ searchParams }: { searchParams: SearchParams }) {
  const session = await requireOfficerSession();
  const filters = readFilters(await searchParams);
  const [reportsResult, summaryResult] = await Promise.all([
    getReports(filters),
    getSummary(),
  ]);
  const reports = reportsResult.data;
  const summary = summaryResult.data;
  const hasFilters = Object.values(filters).some(Boolean);

  return (
    <main className="min-h-screen bg-slate-950 p-4 text-slate-100 md:p-8">
      <section className="mx-auto max-w-6xl">
        <header className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold">CityMind AI Dashboard</h1>
            <p className="mt-2 text-slate-400">
              Decision support for recent citizen reports. Officers make final decisions.
            </p>
            <p className="mt-1 text-xs uppercase tracking-wide text-slate-500">Role: {session.role}</p>
          </div>
          <div className="flex gap-3">
            <Link href="/report" className="min-h-10 rounded-lg border border-blue-700 px-4 py-2 text-sm text-blue-300">Public report form</Link>
            <form action="/api/session/logout" method="post">
              <button type="submit" className="min-h-10 rounded-lg border border-slate-700 px-4 text-sm hover:bg-slate-900">Sign out</button>
            </form>
          </div>
        </header>

        {(reportsResult.error || summaryResult.error) && (
          <div role="alert" className="mt-6 rounded-xl border border-red-900 bg-red-950/40 p-4 text-red-200">
            {reportsResult.error || summaryResult.error}
          </div>
        )}

        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            ["Total Reports", summary.total_reports],
            ["Critical", summary.critical_reports],
            ["Avg Severity", summary.avg_severity],
            ["Top Category", summary.top_category],
          ].map(([label, value]) => (
            <div key={label} className="rounded-xl border border-slate-800 bg-slate-900 p-5">
              <p className="text-sm text-slate-400">{label}</p>
              <p className="mt-2 text-2xl font-bold capitalize">{value}</p>
            </div>
          ))}
        </div>

        <form action="/" method="get" className="mt-8 rounded-xl border border-slate-800 bg-slate-900 p-4 md:p-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="text-xl font-semibold">Report filters</h2>
              <p className="text-sm text-slate-500">Filters run on the full dataset.</p>
            </div>
            <p className="text-sm text-slate-400">Showing {reports.length} reports</p>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <FilterSelect name="status" label="Status" value={filters.status} options={statuses} />
            <FilterSelect name="category" label="Category" value={filters.category} options={categories} />
            <FilterSelect name="priority" label="Priority" value={filters.priority} options={priorities} />
            <label className="grid gap-1 text-sm text-slate-300">
              Min severity
              <input name="min_severity" type="number" min="1" max="5" defaultValue={filters.minSeverity} placeholder="1" className="min-h-11 rounded-lg border border-slate-700 bg-slate-950 px-3" />
            </label>
            <label className="grid gap-1 text-sm text-slate-300">
              Max severity
              <input name="max_severity" type="number" min="1" max="5" defaultValue={filters.maxSeverity} placeholder="5" className="min-h-11 rounded-lg border border-slate-700 bg-slate-950 px-3" />
            </label>
          </div>
          <div className="mt-4 flex flex-wrap gap-3">
            <button type="submit" className="min-h-11 rounded-lg bg-blue-600 px-5 font-semibold hover:bg-blue-500">
              Apply filters
            </button>
            {hasFilters && (
              <Link href="/" className="min-h-11 rounded-lg border border-slate-700 px-5 py-2.5 text-sm font-semibold hover:bg-slate-800">
                Clear filters
              </Link>
            )}
          </div>
        </form>

        <div className="mt-6 grid gap-4">
          {reports.map((report) => (
            <article key={report.report_id} className="rounded-xl border border-slate-800 bg-slate-900 p-4 md:p-5">
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="mr-auto text-xl font-semibold capitalize">
                  {report.category || "Uncategorized"}
                </h2>
                <span className="rounded-full bg-slate-800 px-3 py-1 text-sm capitalize">
                  Priority: {report.priority}
                </span>
                <span className="rounded-full bg-slate-800 px-3 py-1 text-sm capitalize">
                  Status: {report.status ?? "new"}
                </span>
              </div>

              <p className="mt-3 text-slate-300">{report.summary}</p>
              <div className="mt-4 grid gap-2 text-sm text-slate-400 sm:grid-cols-3">
                <p>Severity: {report.severity}/5</p>
                <p>Confidence: {Math.round(report.confidence * 100)}%</p>
                <p>Impact: {report.estimated_impact}</p>
              </div>

              <div className="mt-4 rounded-lg border border-amber-900/60 bg-amber-950/20 p-3 text-sm">
                <p className="font-semibold text-amber-200">AI advisory</p>
                <p className="mt-1 text-slate-300">{report.recommendation}</p>
              </div>

              {report.image_gcs_uri && (
                <div className="mt-4">
                  <p className="mb-2 text-sm font-semibold">Evidence image</p>
                  {/* Private evidence is intentionally served by the API proxy. */}
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={`/api/officer/reports/${report.report_id}/image`} alt="Report evidence" className="max-h-64 max-w-full rounded-lg border border-slate-800 object-contain" />
                </div>
              )}

              <div className="mt-4 flex flex-wrap items-start gap-3">
                <Link href={`/reports/${report.report_id}`} className="min-h-10 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold hover:bg-blue-500">
                  View detail
                </Link>
                <StatusActions reportId={report.report_id} currentStatus={report.status} />
              </div>
            </article>
          ))}

          {!reportsResult.error && reports.length === 0 && (
            <div className="rounded-xl border border-dashed border-slate-700 p-8 text-center text-slate-400">
              <p>{hasFilters ? "No reports match these filters." : "No reports found."}</p>
              {hasFilters && <Link href="/" className="mt-3 inline-block text-blue-400">Clear filters</Link>}
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
