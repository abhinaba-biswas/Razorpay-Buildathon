'use client';

import type { UiState } from '@/types';

interface Props { uiState: UiState | null; }

export default function CartStrip({ uiState }: Props) {
  const isEmpty = !uiState || uiState.cart.length === 0;

  return (
    <div className="flex items-center justify-between border-t border-border px-4 py-2 text-[12px] min-h-[38px] backdrop-blur-sm">
      {isEmpty ? (
        <span className="text-muted/60 flex items-center gap-1.5">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden>
            <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4zM3 6h18M16 10a4 4 0 01-8 0"/>
          </svg>
          Cart is empty
        </span>
      ) : (
        <>
          <span className="text-muted truncate pr-4 flex items-center gap-1.5">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden className="text-accent">
              <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4zM3 6h18M16 10a4 4 0 01-8 0"/>
            </svg>
            {uiState!.cart.map((i) => `${i.name} ×${i.qty}`).join(' · ')}
          </span>
          <span className="shrink-0 font-bold tabular-nums gradient-text">
            ₹{uiState!.total_inr.toLocaleString('en-IN')}
          </span>
        </>
      )}
    </div>
  );
}
