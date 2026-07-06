import Link from "next/link";
import StatusActions from "@/components/StatusActions";

type Props = {
  params: Promise<{ reportId: string }>;
};

async function getReport(reportId: string) {
  const res = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/api/v1/reports/${reportId}`,
    { cache: "no-store" }
  );

  if (!res.ok) return null;
  return res.json();
}

async function getHistory(reportId: string) {
  const res = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/api/v1/reports/${reportId}/status-history`,
    { cache: "no-store" }
  );

  if (!res.ok) return [];
  const data = await res.json();
  return data.items ?? [];
}

export default async function ReportDetail({ params }: Props) {
  const { reportId } = await params;

  const [report, history] = await Promise.all([
    getReport(reportId),
    getHistory(reportId),
  ]);

  if (!report) {
    return (
      <main className="min-h-screen bg-slate-950 p-8 text-slate-100">
        <p>Report not found.</p>
        <Link href="/" className="text-blue-400">Back</Link>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950 p-8 text-slate-100">
      <section className="mx-auto max-w-4xl">
        <Link href="/" className="text-blue-400">← Back to dashboard</Link>

        <h1 className="mt-6 text-3xl font-bold">{report.category}</h1>
        <p className="mt-2 text-slate-400">{report.report_id}</p>

        <div className="mt-6 rounded-xl border border-slate-800 bg-slate-900 p-5">
          <p><b>Priority:</b> {report.priority}</p>
          <p><b>Severity:</b> {report.severity}</p>
          <p><b>Confidence:</b> {Math.round(report.confidence * 100)}%</p>
          <p className="mt-4"><b>Summary:</b> {report.summary}</p>
          <p className="mt-4"><b>Recommendation:</b> {report.recommendation}</p>

          {report.image_gcs_uri && (
            <img
              src={`${process.env.NEXT_PUBLIC_API_URL}/api/v1/reports/${report.report_id}/image`}
              alt="Evidence"
              className="mt-4 max-h-96 rounded-lg border border-slate-800 object-contain"
            />
          )}

          <StatusActions reportId={report.report_id} />
        </div>

        <h2 className="mt-8 text-xl font-semibold">Status History</h2>
        <div className="mt-3 grid gap-3">
          {history.map((item: any, index: number) => (
            <div key={index} className="rounded-lg bg-slate-900 p-4">
              <p><b>{item.status}</b></p>
              <p className="text-sm text-slate-400">{item.created_at}</p>
              {item.note && <p>{item.note}</p>}
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}