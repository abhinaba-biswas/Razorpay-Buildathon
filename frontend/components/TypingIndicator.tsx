'use client';

export default function TypingIndicator() {
  return (
    <div className="self-start animate-slide-up">
      <div className="flex items-center gap-1.5 px-4 py-3 rounded-2xl rounded-bl-sm border border-border backdrop-blur-xl"
        style={{ background: 'var(--c-bubble-agent)' }}>
        <span className="w-1.5 h-1.5 rounded-full bg-muted animate-[dot-bounce_1.4s_infinite_ease-in-out] dot-1" />
        <span className="w-1.5 h-1.5 rounded-full bg-muted animate-[dot-bounce_1.4s_infinite_ease-in-out] dot-2" />
        <span className="w-1.5 h-1.5 rounded-full bg-muted animate-[dot-bounce_1.4s_infinite_ease-in-out] dot-3" />
      </div>
    </div>
  );
}
