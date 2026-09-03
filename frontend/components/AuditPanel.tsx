'use client';

import { useState } from 'react';
import type { AuditRow } from '@/types';

interface Props {
  rows: AuditRow[];
  onReset: () => void;
}

function outcomeConfig(outcome: string) {
  const o = outcome.toLowerCase();
  if (o === 'success' || o === 'paid')
    return { badge: 'bg-success/10 text-success ring-1 ring-success/20', dot: 'bg-success', glow: 'shadow-[0_0_8px_-2px_var(--c-ok)]' };
  if (o === 'rejected')
    return { badge: 'bg-accent/10 text-accent ring-1 ring-accent/20', dot: 'bg-accent', glow: 'shadow-[0_0_8px_-2px_var(--c-accent)]' };
  return { badge: 'bg-fail/10 text-fail ring-1 ring-fail/20', dot: 'bg-fail', glow: 'shadow-[0_0_8px_-2px_var(--c-err)]' };
}

const ACTION_LABELS: Record<string, string> = {
  create_order:        'Create Order',
  create_payment_link: 'Create Payment Link',
  apply_discount:      'Apply Discount',
  get_order_status:    'Check Order Status',
  chat_turn:           'Agent Turn',
  webhook_received:    'Webhook Received',
};

function actionLabel(action: string): string {
  return ACTION_LABELS[action] ?? action.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function AuditRowItem({ row }: { row: AuditRow }) {
  const [open, setOpen] = useState(false);
  const { badge, dot, glow } = outcomeConfig(row.outcome);

  const details: [string, string | null][] = [
    ['Bound check', row.bound_check_result],
    ['Reasoning', row.reasoning],
  ];

  return (
    <div
      onClick={() => setOpen((p) => !p)}
      className={`rounded-xl border cursor-pointer transition-all group
        ${open
          ? 'border-accent/40 bg-panel backdrop-blur-xl ' + glow
          : 'border-border hover:border-muted/40 bg-panel/50 backdrop-blur-sm hover:bg-panel/80'
        }`}
    >
      <div className="px-3 py-2.5">
        {/* Top row */}
        <div className="flex items-center justify-between gap-2 mb-1.5">
          <div className="flex items-center gap-1.5 min-w-0">
            <span className={`shrink-0 w-1.5 h-1.5 rounded-full ${dot} ${open ? 'shadow-sm' : ''}`} />
            <span className="text-[12px] font-semibold text-text-main truncate">
              {actionLabel(row.action)}
            </span>
          </div>
          <span className={`shrink-0 rounded-md px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider ${badge}`}>
            {row.outcome}
          </span>
        </div>

        {row.reasoning && (
          <p className="text-[11px] text-muted leading-relaxed line-clamp-2 mb-1.5">
            {row.reasoning}
          </p>
        )}

        <div className="flex items-center justify-between">
          <span className="text-[10px] text-muted/50">
            {new Date(row.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
          </span>
          <span className={`text-[10px] text-muted/40 transition-transform ${open ? 'rotate-180' : ''}`}>
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden>
              <path d="M2 3.5l3 3 3-3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </span>
        </div>
      </div>

      {/* Expandable detail */}
      <div className={`audit-detail ${open ? 'open' : ''}`}>
        <div className="audit-detail-inner">
          <div className="px-3 pb-2.5 pt-0 space-y-1.5 border-t border-border/50">
            {details.map(([k, v]) =>
              v ? (
                <div key={k} className="text-[10px] leading-relaxed mt-1.5">
                  <span className="text-muted/50">{k}: </span>
                  <span className="text-muted break-all">{v}</span>
                </div>
              ) : null
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function LiveDot() {
  return (
    <span className="relative inline-flex h-1.5 w-1.5 mr-1">
      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-60" />
      <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-success" />
    </span>
  );
}

export default function AuditPanel({ rows, onReset }: Props) {
  return (
    <div className="flex flex-col h-full min-w-0 glass">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-4 border-b border-border shrink-0">
        <div>
          <div className="font-display text-[14px] font-semibold text-text-main tracking-tight flex items-center gap-1.5">
            Audit Trail
          </div>
          <div className="text-[11px] text-muted mt-0.5 flex items-center">
            <LiveDot />
            Read-only · live
          </div>
        </div>
        <button
          onClick={onReset}
          className="text-[10px] font-semibold tracking-wider uppercase px-2.5 py-1.5 rounded-lg
            border border-fail/20 text-fail/50
            hover:border-fail/60 hover:text-fail hover:bg-fail/5
            transition-all"
        >
          Reset
        </button>
      </div>

      {/* Rows */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {rows.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-12">
            <div className="w-10 h-10 rounded-2xl bg-panel border border-border flex items-center justify-center mb-3">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-muted" aria-hidden>
                <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
              </svg>
            </div>
            <p className="text-[12px] text-muted">No actions yet</p>
            <p className="text-[11px] text-muted/50 mt-0.5">Start chatting to see the log</p>
          </div>
        ) : (
          rows.map((r) => <AuditRowItem key={r.id} row={r} />)
        )}
      </div>
    </div>
  );
}
