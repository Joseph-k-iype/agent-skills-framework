import typography from '@tailwindcss/typography'

/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Surfaces
        canvas: '#F6F6F4', // warm stone — the app background
        surface: '#FFFFFF', // cards, panels, topbar
        line: '#E7E7E3', // hairline borders and dividers

        // Ink (text)
        ink: {
          DEFAULT: '#0E0E10', // primary text, headings
          2: '#6B6B70', // secondary text
          3: '#9A9AA0', // tertiary / meta
        },

        // The single accent — a sharp red, used rarely
        accent: {
          50: '#FEF2F0',
          100: '#FDE0DB',
          200: '#FBC3B8',
          300: '#F79A88',
          400: '#F06A50',
          500: '#E5301E',
          600: '#CB2614',
          700: '#A81E10',
          800: '#841A10',
          900: '#6B1810',
        },

        // Muted state colors — used only as small indicator dots, never fills
        ok: '#3F9C6B',
        warn: '#B7791F',
        bad: '#C0392B',
      },
      fontFamily: {
        sans: [
          'Geist Sans',
          'system-ui',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'sans-serif',
        ],
        mono: ['Geist Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      letterSpacing: {
        tightish: '-0.01em',
        eyebrow: '0.14em',
      },
      boxShadow: {
        soft: '0 1px 2px rgba(14,14,16,0.04), 0 6px 20px rgba(14,14,16,0.05)',
        lift: '0 2px 6px rgba(14,14,16,0.06), 0 16px 40px rgba(14,14,16,0.09)',
      },
      borderRadius: {
        xl: '12px',
        '2xl': '16px',
      },
      typography: ({ theme }) => ({
        ink: {
          css: {
            '--tw-prose-body': theme('colors.ink.2'),
            '--tw-prose-headings': theme('colors.ink.DEFAULT'),
            '--tw-prose-lead': theme('colors.ink.2'),
            '--tw-prose-links': theme('colors.accent.600'),
            '--tw-prose-bold': theme('colors.ink.DEFAULT'),
            '--tw-prose-counters': theme('colors.ink.3'),
            '--tw-prose-bullets': theme('colors.ink.3'),
            '--tw-prose-hr': theme('colors.line'),
            '--tw-prose-quotes': theme('colors.ink.DEFAULT'),
            '--tw-prose-quote-borders': theme('colors.accent.500'),
            '--tw-prose-captions': theme('colors.ink.3'),
            '--tw-prose-code': theme('colors.ink.DEFAULT'),
            '--tw-prose-pre-code': theme('colors.ink.DEFAULT'),
            '--tw-prose-pre-bg': theme('colors.canvas'),
            '--tw-prose-th-borders': theme('colors.line'),
            '--tw-prose-td-borders': theme('colors.line'),
          },
        },
      }),
    },
  },
  plugins: [typography],
}
