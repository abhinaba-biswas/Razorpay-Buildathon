'use client';

interface Props {
  url: string;
  total_inr: number;
}

export default function PayCard({ url, total_inr }: Props) {
  return (
    <div className="animate-slide-up self-stretch">
    <div className="rounded-2xl border border-success/25 overflow-hidden backdrop-blur-xl"
      style={{ background: 'var(--c-panel)', boxShadow: '0 0 32px -8px var(--c-ok)' }}>

      {/* Green top strip */}
      <div className="h-0.5 bg-gradient-to-r from-success via-success-2 to-success" />

      <div className="p-4">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-5 h-5 rounded-lg bg-success/15 flex items-center justify-center">
            <svg width="9" height="9" viewBox="0 0 14 14" fill="none" aria-hidden>
              <path d="M2 7l3.5 3.5L12 3" stroke="var(--c-ok)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <span className="text-[10px] font-bold uppercase tracking-[0.1em] text-success">
            Payment ready
          </span>
        </div>

        <div className="font-display text-2xl font-bold text-text-main tabular-nums mb-0.5">
          ₹{total_inr.toLocaleString('en-IN')}
        </div>
        <div className="text-[11px] text-muted mb-4">
          Complete your payment on Razorpay&apos;s secure checkout page.
        </div>

        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 h-10 px-5 rounded-xl bg-success text-success-fg text-[13px] font-bold
            transition-all hover:opacity-90 active:scale-[0.98] glow-ok"
        >
          Pay now
          <svg width="13" height="13" viewBox="0 0 14 14" fill="none" aria-hidden>
            <path d="M2 7h10M7 2l5 5-5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </a>

        <div className="mt-3 flex items-center gap-2 text-[11px] text-muted">
          <span className="relative inline-flex h-1.5 w-1.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-60" />
            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-success" />
          </span>
          Waiting for payment confirmation…
        </div>
      </div>
    </div>
    </div>
  );
}
