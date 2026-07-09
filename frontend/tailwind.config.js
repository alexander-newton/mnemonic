/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        app: 'var(--app-bg)',
        surface: 'var(--app-surface)',
        muted: 'var(--app-text-muted)',
        'border-app': 'var(--app-border)',
      },
    },
  },
  plugins: [],
};
