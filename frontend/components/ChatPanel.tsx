'use client';

import { useEffect, useRef, KeyboardEvent } from 'react';
import type { ChatMessage, UiState } from '@/types';
import GateCard from './GateCard';
import PayCard from './PayCard';
import SuccessCard from './SuccessCard';
import FailureCard from './FailureCard';
import CartStrip from './CartStrip';
import TypingIndicator from './TypingIndicator';

interface Props {
  messages: ChatMessage[];
  uiState: UiState | null;
  busy: boolean;
  isDark: boolean;
  onSend: (text: string) => void;
  onConfirm: () => void;
  onCancel: () => void;
  onToggleTheme: () => void;
}

function SunIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <circle cx="12" cy="12" r="5"/>
      <line x1="12" y1="1" x2="12" y2="3"/>
      <line x1="12" y1="21" x2="12" y2="23"/>
      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
      <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
      <line x1="1" y1="12" x2="3" y2="12"/>
      <line x1="21" y1="12" x2="23" y2="12"/>
      <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
      <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
    </svg>
  );
}

function SendIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <line x1="22" y1="2" x2="11" y2="13"/>
      <polygon points="22 2 15 22 11 13 2 9 22 2"/>
    </svg>
  );
}

function renderAgentMarkdown(raw: string): string {
  let s = raw
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  s = s.replace(/\*\*([^*]+?)\*\*/g, '<strong>$1</strong>');
  s = s.replace(/(?<!\*)\*([^*\n]+?)\*(?!\*)/g, '<em>$1</em>');
  s = s.replace(/`([^`]+?)`/g, '<code style="font-family:monospace;font-size:0.88em;background:var(--c-border);padding:1px 4px;border-radius:4px">$1</code>');
  s = s.replace(
    /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener noreferrer" style="color:var(--c-accent);text-decoration:underline;font-weight:500">$1</a>',
  );
  s = s.replace(/^(\d+)\.\s+/gm, '<strong>$1.</strong>&nbsp;');
  s = s.replace(/\n/g, '<br>');

  return s;
}

function MessageRenderer({
  msg, onConfirm, onCancel, busy,
}: { msg: ChatMessage; onConfirm: () => void; onCancel: () => void; busy: boolean }) {
  if (msg.kind === 'typing')  return <TypingIndicator />;
  if (msg.kind === 'gate')    return <GateCard data={msg.data} onConfirm={onConfirm} onCancel={onCancel} disabled={busy} />;
  if (msg.kind === 'pay')     return <PayCard url={msg.url} total_inr={msg.total_inr} />;
  if (msg.kind === 'success') return <SuccessCard order_id={msg.order_id} total_inr={msg.total_inr} />;
  if (msg.kind === 'failure') return <FailureCard reason={msg.reason} order_id={msg.order_id} />;

  const isUser = msg.kind === 'user';
  return (
    <div
      className={`animate-slide-up max-w-[80%] rounded-2xl px-4 py-3 text-[13.5px] leading-relaxed break-words border-subtle
        ${isUser
          ? 'self-end bg-bubble-user text-text-main rounded-br-sm shadow-sm whitespace-pre-wrap'
          : 'self-start bg-bubble-agent text-text-main rounded-bl-sm backdrop-blur-xl'
        }`}
    >
      {!isUser && (
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-accent mr-2 mb-0.5 align-middle flex-shrink-0" />
      )}
      {isUser
        ? msg.text
        : <span dangerouslySetInnerHTML={{ __html: renderAgentMarkdown(msg.text) }} />
      }
    </div>
  );
}

export default function ChatPanel({ messages, uiState, busy, isDark, onSend, onConfirm, onCancel, onToggleTheme }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef  = useRef<HTMLInputElement>(null);

  useEffect(() => {
    requestAnimationFrame(() => {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
    });
  }, [messages]);

  const submit = () => {
    const val = inputRef.current?.value.trim();
    if (val) {
      if (inputRef.current) inputRef.current.value = '';
      onSend(val);
    }
  };

  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); }
  };

  return (
    <div className="flex flex-col h-full min-w-0 glass border-r border-border">
      {/* Header */}
      <header className="flex items-center justify-between px-5 py-4 border-b border-border backdrop-blur-xl shrink-0">
        <div className="flex items-center gap-3">
          {/* Logo mark */}
          <div className="relative w-8 h-8 rounded-xl bg-accent/15 flex items-center justify-center shrink-0">
            <div className="w-3 h-3 rounded-full bg-accent" />
            <div className="absolute inset-0 rounded-xl ring-1 ring-accent/30" />
          </div>
          <div>
            <div className="font-display text-[15px] font-bold gradient-text tracking-tight leading-none">
              TrustRail
            </div>
            <div className="text-[11px] text-muted mt-1">Checkout agent · actions logged →</div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* TEST MODE badge */}
          <div className="text-[9px] font-bold tracking-[0.12em] uppercase px-2.5 py-1 rounded-lg bg-accent/10 text-accent ring-1 ring-accent/20">
            Test mode
          </div>
          {/* Theme toggle */}
          <button
            onClick={onToggleTheme}
            aria-label="Toggle theme"
            className="w-8 h-8 flex items-center justify-center rounded-xl text-muted hover:text-text-main hover:bg-panel transition-all ring-1 ring-border"
          >
            {isDark ? <SunIcon /> : <MoonIcon />}
          </button>
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-5 flex flex-col gap-3">
        {messages.map((msg) => (
          <MessageRenderer key={msg.id} msg={msg} onConfirm={onConfirm} onCancel={onCancel} busy={busy} />
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Cart strip */}
      <CartStrip uiState={uiState} />

      {/* Input */}
      <div className="flex items-center gap-2.5 px-4 py-3.5 border-t border-border shrink-0">
        <input
          ref={inputRef}
          type="text"
          placeholder="Ask about products or tell me what you want…"
          disabled={busy}
          onKeyDown={onKey}
          autoComplete="off"
          className="flex-1 rounded-xl bg-panel border border-border text-text-main placeholder:text-muted text-[13.5px] px-4 py-2.5 outline-none backdrop-blur-sm
            focus:ring-2 focus:ring-accent/30 focus:border-accent/50 transition-all
            disabled:opacity-40 disabled:cursor-not-allowed"
        />
        <button
          onClick={submit}
          disabled={busy}
          aria-label="Send"
          className="w-10 h-10 flex items-center justify-center rounded-xl bg-accent text-accent-fg shrink-0
            transition-all hover:opacity-90 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed
            glow-accent"
        >
          <SendIcon />
        </button>
      </div>
    </div>
  );
}
