import type { Metadata } from 'next'
import './globals.css'
import { Header } from '@/components/layout/Header'
import { Footer } from '@/components/layout/Footer'
import { Providers } from '@/components/Providers'

export const metadata: Metadata = {
    title: 'Student Resource Library',
    description: 'Enterprise-grade student resource library with unlimited storage',
    keywords: ['student', 'resources', 'library', 'notes', 'exam', 'study materials'],
}

export default function RootLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <html lang="en" className="dark">
            <body className="min-h-screen flex flex-col">
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
