export default function Loading() {
  return (
    <main className="min-h-screen bg-slate-950 p-4 text-slate-100 md:p-8">
      <div className="mx-auto max-w-6xl animate-pulse">
        <div className="h-9 w-72 rounded bg-slate-800" />
        <div className="mt-3 h-5 w-96 max-w-full rounded bg-slate-900" />
        <div className="mt-8 h-72 rounded-xl border border-slate-800 bg-slate-900" />
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((item) => <div key={item} className="h-28 rounded-xl bg-slate-900" />)}
        </div>
      </div>
    </main>
  );
}
