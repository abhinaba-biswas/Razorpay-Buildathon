'use client';

interface Props { reason: string; order_id: string; }

export default function FailureCard({ reason, order_id }: Props) {
  return (
    <div className="animate-slide-up self-stretch">
    <div className="rounded-2xl border border-fail/25 overflow-hidden backdrop-blur-xl"
      style={{ background: 'var(--c-panel)', boxShadow: '0 0 24px -8px var(--c-err)' }}>
      <div className="h-0.5 bg-gradient-to-r from-fail via-fail-2 to-fail" />
      <div className="p-4">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-5 h-5 rounded-lg bg-fail/10 flex items-center justify-center">
            <svg width="9" height="9" viewBox="0 0 14 14" fill="none" aria-hidden>
              <path d="M3 3l8 8M11 3L3 11" stroke="var(--c-err)" strokeWidth="1.8" strokeLinecap="round"/>
            </svg>
          </div>
          <span className="text-[10px] font-bold uppercase tracking-[0.1em] text-fail">Payment failed</span>
        </div>
        <div className="text-[14px] font-semibold text-text-main mb-1">The payment didn&apos;t go through</div>
        <div className="text-[11px] text-muted mb-1">
          {reason || 'The card was declined.'}
          {order_id && <> Order <span className="font-mono">{order_id}</span></>}
        </div>
        <div className="text-[11px] text-muted/70">
          Try again with a different card — just ask.
        </div>
      </div>
    </div>
    </div>
  );
}
