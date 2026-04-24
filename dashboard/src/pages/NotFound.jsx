import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <section className="soc-glass p-6 md:p-8">
      <p className="soc-kicker">Navigation Error</p>
      <h1 className="soc-title mt-2">The page you requested does not exist.</h1>
      <p className="mt-3 text-sm text-soc-muted">Return to the main operational dashboard to continue monitoring.</p>
      <Link
        to="/"
        className="mt-5 inline-flex rounded-full border border-soc-electric/40 bg-soc-electric/15 px-4 py-2 text-xs font-semibold uppercase tracking-[0.16em] text-soc-electric"
      >
        Go to overview
      </Link>
    </section>
  );
}
