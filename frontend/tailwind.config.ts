import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: 'class',
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        /* All colors are CSS-variable–driven so they flip with theme */
        bg:             'var(--c-bg)',
        panel:          'var(--c-panel)',
        border:         'var(--c-border)',
        'text-main':    'var(--c-text)',
        muted:          'var(--c-muted)',
        accent:         'var(--c-accent)',
        'accent-fg':    'var(--c-accent-fg)',
        success:        'var(--c-ok)',
        fail:           'var(--c-err)',
        'bubble-agent': 'var(--c-bubble-agent)',
        'bubble-user':  'var(--c-bubble-user)',
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Fira Code"', 'Menlo', 'monospace'],
      },
      animation: {
        pulse2:         'pulse2 1.5s ease-in-out infinite',
        'dot-bounce':   'dot-bounce 1.4s infinite ease-in-out',
        'slide-up':     'slide-up 0.22s cubic-bezier(.16,1,.3,1)',
        'border-spin':  'border-spin 4s linear infinite',
        'fade-in':      'fade-in 0.3s ease-out',
      },
      keyframes: {
        pulse2:       { '0%,100%': { opacity: '1' }, '50%': { opacity: '0.25' } },
        'dot-bounce': { '0%,80%,100%': { transform: 'translateY(0)' }, '40%': { transform: 'translateY(-5px)' } },
        'slide-up':   { from: { opacity: '0', transform: 'translateY(8px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
        'border-spin':{ to: { '--border-angle': '360deg' } },
        'fade-in':    { from: { opacity: '0' }, to: { opacity: '1' } },
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
      },
      boxShadow: {
        'glow-accent':  '0 0 20px -4px var(--c-accent)',
        'glow-ok':      '0 0 20px -4px var(--c-ok)',
        'glow-err':     '0 0 20px -4px var(--c-err)',
        'glass':        '0 8px 32px 0 rgba(0,0,0,0.18)',
        'glass-light':  '0 8px 32px 0 rgba(0,0,0,0.07)',
      },
      backdropBlur: { xs: '4px' },
    },
  },
  plugins: [],
};

export default config;
