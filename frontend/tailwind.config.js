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
                // MediaPeek-inspired dark theme
                background: {
                    primary: '#0a0a0a',
                    secondary: '#141414',
                    tertiary: '#1e1e1e',
                },
                border: {
                    subtle: '#2a2a2a',
                    medium: '#3a3a3a',
                    strong: '#4a4a4a',
                },
                text: {
                    primary: '#e8e8e8',
                    secondary: '#a8a8a8',
                    muted: '#707070',
                },
                accent: {
                    primary: '#3b82f6',
                    hover: '#2563eb',
                    light: '#60a5fa',
                },
            },
            fontFamily: {
                sans: ['-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
                mono: ['SF Mono', 'Consolas', 'Courier New', 'monospace'],
            },
            borderRadius: {
                sm: '4px',
                md: '6px',
                lg: '8px',
            },
            animation: {
                'fade-in': 'fadeIn 0.3s ease-out',
                'slide-up': 'slideUp 0.3s ease-out',
            },
            keyframes: {
                fadeIn: {
                    '0%': { opacity: '0' },
                    '100%': { opacity: '1' },
                },
                slideUp: {
                    '0%': { opacity: '0', transform: 'translateY(10px)' },
                    '100%': { opacity: '1', transform: 'translateY(0)' },
                },
            },
        },
    },
    plugins: [],
}
