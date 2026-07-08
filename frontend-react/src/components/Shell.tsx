import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

export function Shell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link to="/" className="text-lg font-semibold tracking-tight">
            Diafanis
          </Link>
          <span className="text-xs text-slate-400">
            Independent valuation estimates for private market funds
          </span>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
      <footer className="mx-auto max-w-6xl px-6 pb-10">
        <p className="border-t border-slate-200 pt-6 text-xs leading-relaxed text-slate-400">
          All figures are model-estimated, not GP-reported. Estimates are built from public
          benchmark comps using a pacing model, calibrated to the last publicly disclosed mark
          where one exists. Fund names, sizes and marks are indicative figures compiled from
          public sources. Nothing here is investment advice.
        </p>
      </footer>
    </div>
  )
}
