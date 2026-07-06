import Link from "next/link";

import ReportForm from "@/components/ReportForm";

export default function PublicReportPage() {
  return (
    <main className="min-h-screen bg-slate-950 p-4 text-slate-100 md:p-8">
      <section className="mx-auto max-w-3xl">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-3xl font-bold">Report a community issue</h1>
            <p className="mt-2 text-slate-400">Send facts, location, and optional evidence.</p>
          </div>
          <Link href="/login" className="text-sm text-blue-400">Officer sign in</Link>
        </header>
        <ReportForm />
      </section>
    </main>
  );
}
