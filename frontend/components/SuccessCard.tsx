'use client';

interface Props { order_id: string; total_inr: number; }

export default function SuccessCard({ order_id, total_inr }: Props) {
  return (
    <div className="animate-slide-up self-stretch rounded-2xl border border-success/25 overflow-hidden backdrop-blur-xl"
      style={{ background: 'var(--c-panel)', boxShadow: '0 0 24px -6px var(--c-ok)' }}>
      <div className="h-0.5 bg-gradient-to-r from-success via-emerald-300 to-success" />
      <div className="p-4">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-5 h-5 rounded-lg bg-success/15 flex items-center justify-center">
            <svg width="9" height="9" viewBox="0 0 14 14" fill="none" aria-hidden>
              <path d="M2 7l3.5 3.5L12 3" stroke="var(--c-ok)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <span className="text-[10px] font-bold uppercase tracking-[0.1em] text-success">Payment confirmed</span>
        </div>
        <div className="text-xl font-bold text-text-main mb-1">
          ₹{total_inr.toLocaleString('en-IN')} received
        </div>
        <div className="text-[11px] text-muted">
          Order <span className="font-mono">{order_id}</span> is complete. Thank you!
        </div>
      </div>
    </div>
  );
}
