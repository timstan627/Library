/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,
    output: 'standalone',
    env: {
        NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || '',
    },
    images: {
        remotePatterns: [
            {
                protocol: 'https',
                hostname: '**',
            },
        ],
    },
    // Proxy API requests to backend in development (Nginx handles this in prod)
    async rewrites() {
        const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000'
        return [
            {
                source: '/api/:path*',
                destination: `${backendUrl}/api/:path*`,
            },
        ]
    },
}

module.exports = nextConfig
