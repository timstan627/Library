/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: 'class',
    content: [
        './pages/**/*.{js,ts,jsx,tsx,mdx}',
        './components/**/*.{js,ts,jsx,tsx,mdx}',
        './app/**/*.{js,ts,jsx,tsx,mdx}',
    ],
    theme: {
        extend: {
            colors: {
                // Midnight surfaces — tinted neutrals, one azure-blue anchor hue.
                // Vars hold "R G B" triplets so alpha (<alpha-value>) keeps working.
                background: {
                    primary: 'rgb(var(--bg-primary) / <alpha-value>)',
                    secondary: 'rgb(var(--bg-secondary) / <alpha-value>)',
                    tertiary: 'rgb(var(--bg-tertiary) / <alpha-value>)',
                },
                border: {
                    subtle: 'rgb(var(--border-subtle) / <alpha-value>)',
                    medium: 'rgb(var(--border-medium) / <alpha-value>)',
                    strong: 'rgb(var(--border-strong) / <alpha-value>)',
                },
                text: {
                    primary: 'rgb(var(--text-primary) / <alpha-value>)',
                    secondary: 'rgb(var(--text-secondary) / <alpha-value>)',
                    muted: 'rgb(var(--text-muted) / <alpha-value>)',
                },
                accent: {
                    primary: 'rgb(var(--accent-primary) / <alpha-value>)',
                    hover: 'rgb(var(--accent-hover) / <alpha-value>)',
                    light: 'rgb(var(--accent-light) / <alpha-value>)',
                    bright: 'rgb(var(--accent-bright) / <alpha-value>)',
                    ink: 'rgb(var(--accent-ink) / <alpha-value>)',
                },
                ink: {
                    strong: 'rgb(var(--ink-strong) / <alpha-value>)',
                },
                success: {
                    DEFAULT: 'rgb(var(--success) / <alpha-value>)',
                    light: 'rgb(var(--success-light) / <alpha-value>)',
                },
                warning: {
                    DEFAULT: 'rgb(var(--warning) / <alpha-value>)',
                    light: 'rgb(var(--warning-light) / <alpha-value>)',
                },
                danger: {
                    DEFAULT: 'rgb(var(--danger) / <alpha-value>)',
                    hover: 'rgb(var(--danger-hover) / <alpha-value>)',
                    light: 'rgb(var(--danger-light) / <alpha-value>)',
                },
                violet: {
                    light: 'rgb(var(--violet-light) / <alpha-value>)',
                },

                // ------------------------------------------------------------------
                // Legacy palette bridge. Framework default steps were once referenced
                // directly across pages; each step now resolves to the themed token
                // instead, so existing markup renders on-system without churn.
                // Text steps resolve to the light (>=4.5:1 on dark) variants.
                // ------------------------------------------------------------------
                red: {
                    300: 'rgb(var(--danger-light) / <alpha-value>)',
                    400: 'rgb(var(--danger-light) / <alpha-value>)',
                    500: 'rgb(var(--danger-light) / <alpha-value>)',
                    600: 'rgb(var(--danger-light) / <alpha-value>)',
                    700: 'rgb(var(--danger) / <alpha-value>)',
                },
                green: {
                    500: 'rgb(var(--success-light) / <alpha-value>)',
                    600: 'rgb(var(--success-light) / <alpha-value>)',
                },
                yellow: {
                    500: 'rgb(var(--warning) / <alpha-value>)',
                },
                blue: {
                    400: 'rgb(var(--accent-light) / <alpha-value>)',
                    500: 'rgb(var(--accent-light) / <alpha-value>)',
                    600: 'rgb(var(--accent-light) / <alpha-value>)',
                },
                purple: {
                    400: 'rgb(var(--violet-light) / <alpha-value>)',
                    500: 'rgb(var(--violet-light) / <alpha-value>)',
                    600: 'rgb(var(--violet-light) / <alpha-value>)',
                },
                orange: {
                    500: 'rgb(var(--warning) / <alpha-value>)',
                },
                amber: {
                    300: 'rgb(var(--warning-light) / <alpha-value>)',
                    400: 'rgb(var(--warning-light) / <alpha-value>)',
                    500: 'rgb(var(--warning) / <alpha-value>)',
                },
                gray: {
                    200: 'rgb(var(--border-medium) / <alpha-value>)',
                    300: 'rgb(var(--text-muted) / <alpha-value>)',
                    400: 'rgb(var(--text-muted) / <alpha-value>)',
                    500: 'rgb(var(--text-muted) / <alpha-value>)',
                    600: 'rgb(var(--border-medium) / <alpha-value>)',
                    700: 'rgb(var(--text-secondary) / <alpha-value>)',
                    800: 'rgb(var(--bg-tertiary) / <alpha-value>)',
                    900: 'rgb(var(--bg-secondary) / <alpha-value>)',
                },
                white: 'rgb(var(--accent-ink) / <alpha-value>)',
                black: 'rgb(var(--ink-strong) / <alpha-value>)',
            },
            fontFamily: {
                sans: ['var(--font-body)', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
                display: ['var(--font-display)', 'var(--font-body)', 'system-ui', 'sans-serif'],
                mono: ['ui-monospace', 'SFMono-Regular', 'Consolas', 'Liberation Mono', 'monospace'],
            },
            borderRadius: {
                sm: '4px',
                md: '6px',
                lg: '8px',
            },
            transitionTimingFunction: {
                expo: 'var(--ease-out-expo)',
            },
        },
    },
    plugins: [],
}
