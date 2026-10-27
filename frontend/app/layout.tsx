import type { Metadata, Viewport } from 'next'
import NextTopLoader from 'nextjs-toploader'
import { Bricolage_Grotesque, Figtree } from 'next/font/google'
import './globals.css'
import { Header } from '@/components/layout/Header'
import { Footer } from '@/components/layout/Footer'
import { Providers } from '@/components/Providers'

// Display face with real character; body face tuned for UI legibility.
// Both ship variable-weight, swap-loaded, with metric-conscious fallbacks.
const fontDisplay = Bricolage_Grotesque({
    subsets: ['latin'],
    variable: '--font-display',
    display: 'swap',
})

const fontBody = Figtree({
    subsets: ['latin'],
    variable: '--font-body',
    display: 'swap',
})

export const metadata: Metadata = {
    title: {
        default: 'Student Library',
        template: '%s · Student Library',
    },
    description: 'Share and discover study materials, notes, and exam papers with your peers.',
    keywords: ['student', 'resources', 'library', 'notes', 'exam', 'study materials'],
}

export const viewport: Viewport = {
    themeColor: '#080d11',
}

export default function RootLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <html lang="en" className={`${fontDisplay.variable} ${fontBody.variable} dark`}>
            <body className="min-h-screen flex flex-col">
                {/* Route-change progress: harbor blue, no glow, no spinner */}
                <NextTopLoader
                    color="rgb(0 113 211)"
                    height={3}
                    showSpinner={false}
                    shadow={false}
                />
                <Providers>
                    <Header />
                    <main className="flex-1">
                        {children}
                    </main>
                    <Footer />
                </Providers>
            </body>
        </html>
    )
}
