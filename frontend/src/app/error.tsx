"use client";

import { useEffect } from "react";

export default function ErrorPage({
  error,
  unstable_retry,
}: {
  error: Error & { digest?: string };
  unstable_retry: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="min-h-screen bg-slate-950 p-8 text-slate-100">
      <section className="mx-auto max-w-xl rounded-xl border border-red-900 bg-slate-900 p-6">
        <h1 className="text-xl font-semibold">Dashboard unavailable</h1>
        <p className="mt-2 text-slate-400">An unexpected error stopped this page.</p>
        <button type="button" onClick={() => unstable_retry()} className="mt-5 rounded-lg bg-blue-600 px-4 py-2 font-semibold hover:bg-blue-500">
          Try again
        </button>
      </section>
    </main>
  );
}
