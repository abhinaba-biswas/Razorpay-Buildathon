'use client';

import type { PendingConfirmation } from '@/types';

interface Props {
  data: PendingConfirmation;
  onConfirm: () => void;
  onCancel: () => void;
  disabled?: boolean;
}

export default function GateCard({ data, onConfirm, onCancel, disabled }: Props) {
  const fmt = (n: number) => n.toLocaleString('en-IN');

  return (
    /* Outer wrapper creates the animated conic-gradient border */
    <div className="gate-border self-stretch animate-slide-up">
      {/* Inner card — sits above the pseudo-element */}
      <div className="relative z-10 rounded-[13px] overflow-hidden"
        style={{ background: 'var(--c-panel)', backdropFilter: 'blur(20px)' }}>

        {/* Accent top bar */}
        <div className="h-0.5 w-full bg-gradient-to-r from-accent via-orange-300 to-accent" />

        <div className="p-4">
          {/* Label */}
          <div className="flex items-center gap-2 mb-3">
            <div className="w-5 h-5 rounded-lg bg-accent/15 flex items-center justify-center">
              <svg width="10" height="10" viewBox="0 0 14 14" fill="none" aria-hidden>
                <path d="M7 2v6M7 10.5v1" stroke="var(--c-accent)" strokeWidth="2" strokeLinecap="round"/>
              </svg>
            </div>
            <span className="text-[10px] font-bold uppercase tracking-[0.1em] text-accent">
              Confirmation required
            </span>
          </div>

          {/* Items list */}
          <div className="mb-3 space-y-1">
            {data.items.map((item, i) => (
              <div key={i} className="flex items-center justify-between text-[13px]">
                <span className="text-text-main font-medium">{item.name}</span>
                <span className="text-muted text-xs">×{item.qty}</span>
              </div>
            ))}
          </div>

          {/* Divider */}
          <div className="border-t border-border my-2.5" />

          {/* Total */}
          <div className="flex items-baseline justify-between mb-1.5">
            <span className="text-[11px] text-muted uppercase tracking-wider">Total</span>
            <span className="text-2xl font-bold gradient-text tabular-nums">₹{fmt(data.total_inr)}</span>
          </div>
          <p className="text-[11px] text-muted mb-4">
            Action: creating a Razorpay payment link for ₹{fmt(data.total_inr)}
          </p>

          {/* Actions */}
          <div className="flex gap-2">
            <button
              onClick={onConfirm}
              disabled={disabled}
              className="flex-1 h-10 rounded-xl bg-accent text-accent-fg text-[13px] font-bold
                transition-all hover:opacity-90 active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed
                glow-accent"
            >
              Confirm order
            </button>
            <button
              onClick={onCancel}
              disabled={disabled}
              className="h-10 px-4 rounded-xl border border-border text-[13px] text-muted
                hover:border-muted/60 hover:text-text-main transition-all
                disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
