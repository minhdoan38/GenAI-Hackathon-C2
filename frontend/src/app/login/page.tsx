type Props = {
  searchParams: Promise<{ error?: string }>;
};

export default async function LoginPage({ searchParams }: Props) {
  const { error } = await searchParams;
  return (
    <main className="grid min-h-screen place-items-center bg-slate-950 p-4 text-slate-100">
      <section className="w-full max-w-md rounded-xl border border-slate-800 bg-slate-900 p-6">
        <h1 className="text-2xl font-bold">Officer sign in</h1>
        <p className="mt-2 text-sm text-slate-400">Protected CityMind operations dashboard.</p>
        <form action="/api/session/login" method="post" className="mt-6">
          <label className="grid gap-2 text-sm text-slate-300">
            Access password
            <input name="password" type="password" required autoComplete="current-password" className="min-h-11 rounded-lg border border-slate-700 bg-slate-950 px-3 text-base" />
          </label>
          {error && <p role="alert" className="mt-3 text-sm text-red-300">Invalid password.</p>}
          <button type="submit" className="mt-5 min-h-11 w-full rounded-lg bg-blue-600 font-semibold hover:bg-blue-500">Sign in</button>
        </form>
        <a href="/report" className="mt-5 inline-block text-sm text-blue-400">Submit a public report</a>
      </section>
    </main>
  );
}
