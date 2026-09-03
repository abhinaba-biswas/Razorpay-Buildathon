'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import ChatPanel from '@/components/ChatPanel';
import AuditPanel from '@/components/AuditPanel';
import type { AuditRow, ChatMessage, UiState } from '@/types';

let _seq = 0;
const uid = () => String(++_seq);
const genSid = () => 'sess_' + Math.random().toString(36).slice(2, 10);

export default function Home() {
  /* ── Theme ───────────────────────────────────────────────────── */
  const [isDark, setIsDark] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem('theme');
    const dark = stored !== 'light';
    setIsDark(dark);
    document.documentElement.classList.toggle('dark', dark);
  }, []);

  const toggleTheme = useCallback(() => {
    setIsDark((prev) => {
      const next = !prev;
      document.documentElement.classList.toggle('dark', next);
      localStorage.setItem('theme', next ? 'dark' : 'light');
      return next;
    });
  }, []);

  /* ── Session ─────────────────────────────────────────────────── */
  const [sessionId] = useState<string>(() => genSid());

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: uid(),
      kind: 'agent',
      text: "Hi — I'm the Nimbus Gear checkout assistant.\n\nAsk me what we sell, add items to your cart, and I'll handle the payment. Everything I do is logged in the audit trail on the right.",
    },
  ]);
  const [uiState, setUiState]     = useState<UiState | null>(null);
  const [busy, setBusy]           = useState(false);
  const [auditRows, setAuditRows] = useState<AuditRow[]>([]);
  const lastAuditCount            = useRef(0);

  /* ── Send ────────────────────────────────────────────────────── */
  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || busy) return;
      setBusy(true);
      const typingId = uid();

      setMessages((p) => [
        ...p,
        { id: uid(), kind: 'user', text },
        { id: typingId, kind: 'typing' },
      ]);

      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sessionId, message: text }),
        });

        setMessages((p) => p.filter((m) => m.id !== typingId));

        if (!res.ok) {
          const d = await res.json().catch(() => ({}));
          setMessages((p) => [
            ...p,
            { id: uid(), kind: 'failure', reason: d?.detail || 'Server error.', order_id: '' },
          ]);
          return;
        }

        const data = await res.json();
        const next: ChatMessage[] = [];
        if (data.reply_text) next.push({ id: uid(), kind: 'agent', text: data.reply_text });
        if (data.pending_confirmation)
          next.push({ id: uid(), kind: 'gate', data: data.pending_confirmation });
        if (data.payment_link) {
          const total = data.ui_state?.total_inr ?? data.pending_confirmation?.total_inr ?? 0;
          next.push({ id: uid(), kind: 'pay', url: data.payment_link, total_inr: total });
        }
        setMessages((p) => [...p, ...next]);
        setUiState(data.ui_state ?? null);
      } catch {
        setMessages((p) => [
          ...p.filter((m) => m.id !== typingId),
          { id: uid(), kind: 'agent', text: 'Connection issue — please try again.' },
        ]);
      } finally {
        setBusy(false);
      }
    },
    [busy, sessionId],
  );

  const handleConfirm = useCallback(() => sendMessage('confirm'), [sendMessage]);
  const handleCancel  = useCallback(() => sendMessage('cancel'),  [sendMessage]);

  /* ── Notification polling ─────────────────────────────────────── */
  useEffect(() => {
    const poll = async () => {
      try {
        const res  = await fetch(`/api/notifications/${encodeURIComponent(sessionId)}`);
        const data = await res.json();
        const n    = data.notification;
        if (!n) return;
        if (n.type === 'payment_success') {
          setMessages((p) => [...p, { id: uid(), kind: 'success', order_id: n.order_id, total_inr: n.total_inr }]);
          setUiState({ cart: [], total_inr: 0 });
        } else if (n.type === 'payment_failed') {
          setMessages((p) => [...p, { id: uid(), kind: 'failure', reason: n.reason ?? '', order_id: n.order_id }]);
        }
      } catch { /* transient */ }
    };
    const id = setInterval(poll, 3000);
    return () => clearInterval(id);
  }, [sessionId]);

  /* ── Audit polling ───────────────────────────────────────────── */
  useEffect(() => {
    const poll = async () => {
      try {
        const rows: AuditRow[] = await fetch('/api/audit').then((r) => r.json());
        if (rows.length === lastAuditCount.current) return;
        lastAuditCount.current = rows.length;
        setAuditRows(rows);
      } catch { /* transient */ }
    };
    poll();
    const id = setInterval(poll, 3000);
    return () => clearInterval(id);
  }, []);

  /* ── Reset ───────────────────────────────────────────────────── */
  const handleReset = useCallback(async () => {
    if (!confirm('Reset all demo data? This clears orders, sessions, and audit logs.')) return;
    try {
      await fetch('/api/demo/reset', { method: 'POST' });
      window.location.reload();
    } catch {
      alert('Reset failed — check the server.');
    }
  }, []);

  return (
    <div className="relative flex flex-col md:flex-row h-screen overflow-hidden bg-bg">

      {/* ── Ambient gradient blobs ── */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden -z-10" aria-hidden>
        <div
          className="absolute -top-32 -right-32 w-[600px] h-[600px] rounded-full opacity-100"
          style={{ background: 'var(--c-blob1)', filter: 'blur(100px)' }}
        />
        <div
          className="absolute top-1/2 -left-48 w-[500px] h-[500px] rounded-full"
          style={{ background: 'var(--c-blob2)', filter: 'blur(120px)' }}
        />
        <div
          className="absolute -bottom-32 right-1/3 w-[400px] h-[400px] rounded-full"
          style={{ background: 'var(--c-blob3)', filter: 'blur(90px)' }}
        />
      </div>

      {/* ── Chat panel — 65% ── */}
      <div className="flex flex-col h-[60vh] md:h-full md:flex-[65] min-w-0">
        <ChatPanel
          messages={messages}
          uiState={uiState}
          busy={busy}
          isDark={isDark}
          onSend={sendMessage}
          onConfirm={handleConfirm}
          onCancel={handleCancel}
          onToggleTheme={toggleTheme}
        />
      </div>

      {/* ── Audit panel — 35% ── */}
      <div className="flex flex-col flex-1 md:flex-[35] min-w-0 border-t md:border-t-0 md:border-l border-border">
        <AuditPanel rows={auditRows} onReset={handleReset} />
      </div>
    </div>
  );
}
