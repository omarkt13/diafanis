import { useState } from 'react'
import type { TransferData, Wallet } from './types'

const input = 'h-9 w-28 rounded border border-line bg-raise px-2 text-right tabular-nums outline-none focus:border-brand'

export function WalletDialog({ wallet, transfers, onSave, onClose }: { wallet: Wallet; transfers: TransferData; onSave: (w: Wallet) => void; onClose: () => void }) {
  const [w, setW] = useState<Wallet>(wallet)
  const num = (v: string) => Math.max(0, Math.round(Number(v.replace(/[^\d]/g, '')) || 0))
  const setP = (id: string, v: string) => setW({ ...w, programs: { ...w.programs, [id]: num(v) } })
  const setC = (id: string, v: string) => setW({ ...w, currencies: { ...w.currencies, [id]: num(v) } })

  return (
    <div className="fixed inset-0 z-40 flex items-start justify-center overflow-y-auto bg-black/40 p-4" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div role="dialog" aria-modal="true" aria-label="Wallet" className="my-8 w-full max-w-lg rounded-lg bg-raise p-6 shadow-xl">
        <h2 className="text-xl">Your points</h2>
        <p className="mt-1 text-sm text-sub">Enter your balances. The list then shows which awards you can book now, and from which points.</p>

        <h3 className="mt-5 mb-2 text-sm font-medium text-sub">Bank and hotel points</h3>
        {transfers.currencies.map((c) => (
          <label key={c.id} className="flex items-center justify-between gap-3 py-1.5">
            <span>{c.name}<span className="block text-xs text-sub">{c.note}</span></span>
            <input className={input} inputMode="numeric" value={w.currencies[c.id] || ''} placeholder="0" onChange={(e) => setC(c.id, e.target.value)} />
          </label>
        ))}

        <h3 className="mt-5 mb-2 text-sm font-medium text-sub">Airline miles</h3>
        <div className="max-h-72 overflow-y-auto pr-1">
          {transfers.programs.map((p) => (
            <label key={p.id} className="flex items-center justify-between gap-3 py-1">
              <span>{p.name}</span>
              <input className={input} inputMode="numeric" value={w.programs[p.id] || ''} placeholder="0" onChange={(e) => setP(p.id, e.target.value)} />
            </label>
          ))}
        </div>

        <p className="mt-4 text-xs text-sub">Balances stay in this browser. Transfer partners are in backend/app/data/transfers.json. Edit that file for your cards.</p>
        <div className="mt-5 flex justify-end gap-2">
          <button className="rounded-full px-4 py-2 text-sm font-medium text-brand hover:bg-hover" onClick={onClose}>Cancel</button>
          <button className="rounded-full bg-brand px-5 py-2 text-sm font-medium text-page" onClick={() => { onSave(w); onClose() }}>Save</button>
        </div>
      </div>
    </div>
  )
}
