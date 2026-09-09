/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      colors: {
        canvas: 'var(--bg-canvas)',
        surface: 'var(--bg-surface)',
        'surface-frosted': 'var(--bg-surface-frosted)',
        'accent-primary': 'var(--accent-primary)',
        'accent-hover': 'var(--accent-hover)',
        'accent-subtle': 'var(--accent-subtle)',
      },
      boxShadow: {
        glass: 'var(--shadow-glass)',
        'glass-elevated': 'var(--shadow-glass-elevated)',
      },
      backdropBlur: {
        'xl': '20px',
        '2xl': '32px',
      },
      borderRadius: {
        'squircle-sm': 'var(--squircle-sm)',
        'squircle-md': 'var(--squircle-md)',
        'squircle-lg': 'var(--squircle-lg)',
        'squircle-xl': 'var(--squircle-xl)',
      },
    },
  },
  plugins: [],
}
