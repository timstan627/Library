'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Search, Upload, Download, FileText, Star, TrendingUp } from 'lucide-react'
import { useAuth } from '@/lib/auth-context'

interface Stats {
    resources: number
    users: number
    downloads: number
    courses: number
}

export default function HomePage() {
    const [stats, setStats] = useState<Stats | null>(null)
    const [searchQuery, setSearchQuery] = useState('')
    const { user } = useAuth()
    const router = useRouter()

    useEffect(() => {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'
        fetch(`${apiUrl}/api/v1/stats`)
            .then(res => res.json())
            .then(data => setStats(data))
            .catch(() => setStats({ resources: 0, users: 0, downloads: 0, courses: 0 }))
    }, [])

    const formatNumber = (num: number) => {
        if (num >= 1000) return `${(num / 1000).toFixed(1)}K+`
        return num.toString()
    }

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault()
        if (searchQuery.trim()) {
            router.push(`/browse?q=${encodeURIComponent(searchQuery.trim())}`)
        }
    }

    return (
        <div className="min-h-screen">
            {/* Hero Section */}
            <section className="container-custom py-16 text-center">
                <div className="max-w-3xl mx-auto">
                    <h1 className="text-4xl md:text-5xl font-bold text-text-primary mb-6 animate-fade-in">
                        Student Resource{' '}
                        <span className="text-gradient">Library</span>
                    </h1>
                    <p className="text-xl text-text-secondary mb-8 animate-slide-up">
                        Share and discover study materials, notes, and exam papers.
                        Enterprise-grade cloud storage with unlimited capacity.
                    </p>

                    {/* Search Bar */}
                    <form onSubmit={handleSearch} className="flex items-center max-w-xl mx-auto mb-8 animate-slide-up">
                        <div className="relative flex-1">
                            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
                            <input
                                type="text"
                                placeholder="Search for notes, exams, courses..."
                                className="input pl-12 pr-4 py-3 text-lg"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                            />
                        </div>
                        <button type="submit" className="btn btn-primary ml-3 py-3 px-6">
                            Search
                        </button>
                    </form>

                    {/* Quick Links */}
                    <div className="flex flex-wrap justify-center gap-4">
                        <Link href="/browse" className="btn btn-secondary">
                            <FileText className="w-4 h-4 mr-2" />
                            Browse All
                        </Link>
                        {user && (
                            <Link href="/upload" className="btn btn-secondary">
                                <Upload className="w-4 h-4 mr-2" />
                                Upload Resource
                            </Link>
                        )}
                        {!user && (
                            <Link href="/auth/register" className="btn btn-secondary">
                                <Star className="w-4 h-4 mr-2" />
                                Join Now
                            </Link>
                        )}
                    </div>
                </div>
            </section>

            {/* Stats Section - LIVE COUNTS */}
            <section className="border-y border-border-subtle bg-background-secondary py-8">
                <div className="container-custom">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
                        <div>
                            <p className="text-3xl font-bold text-accent-primary mb-2">
                                {stats ? formatNumber(stats.resources) : '...'}
                            </p>
                            <p className="text-text-secondary">Resources</p>
                        </div>
                        <div>
                            <p className="text-3xl font-bold text-accent-primary mb-2">
                                {stats ? formatNumber(stats.users) : '...'}
                            </p>
                            <p className="text-text-secondary">Users</p>
                        </div>
                        <div>
                            <p className="text-3xl font-bold text-accent-primary mb-2">
                                {stats ? formatNumber(stats.downloads) : '...'}
                            </p>
                            <p className="text-text-secondary">Downloads</p>
                        </div>
                        <div>
                            <p className="text-3xl font-bold text-accent-primary mb-2">
                                {stats ? formatNumber(stats.courses) : '...'}
                            </p>
                            <p className="text-text-secondary">Courses</p>
                        </div>
                    </div>
                </div>
            </section>

            {/* Features Section */}
            <section className="container-custom py-12">
                <h2 className="text-2xl font-bold text-text-primary text-center mb-12">
                    Why Use Student Library?
                </h2>

                <div className="grid md:grid-cols-3 gap-8">
                    <div className="card p-6">
                        <div className="w-12 h-12 bg-accent-primary/10 rounded-lg flex items-center justify-center mb-4">
                            <Upload className="w-6 h-6 text-accent-primary" />
                        </div>
                        <h3 className="text-lg font-semibold text-text-primary mb-2">
                            Unlimited Storage
                        </h3>
                        <p className="text-text-secondary">
                            Upload your notes, exams, and study materials without worrying about storage limits.
                        </p>
                    </div>

                    <div className="card p-6">
                        <div className="w-12 h-12 bg-accent-primary/10 rounded-lg flex items-center justify-center mb-4">
                            <Search className="w-6 h-6 text-accent-primary" />
                        </div>
                        <h3 className="text-lg font-semibold text-text-primary mb-2">
                            Advanced Search
                        </h3>
                        <p className="text-text-secondary">
                            Find exactly what you need with powerful filters by course, department, and tags.
                        </p>
                    </div>

                    <div className="card p-6">
                        <div className="w-12 h-12 bg-accent-primary/10 rounded-lg flex items-center justify-center mb-4">
                            <Star className="w-6 h-6 text-accent-primary" />
                        </div>
                        <h3 className="text-lg font-semibold text-text-primary mb-2">
                            Community Ratings
                        </h3>
                        <p className="text-text-secondary">
                            Rate and review resources to help others find the best study materials.
                        </p>
                    </div>
                </div>
            </section>

            {/* CTA Section */}
            <section className="container-custom py-12">
                <div className="card p-8 md:p-12 text-center bg-gradient-to-r from-background-secondary to-background-tertiary">
                    {user ? (
                        <>
                            <h2 className="text-2xl md:text-3xl font-bold text-text-primary mb-4">
                                Welcome Back, {(user.display_name || 'User').split(' ')[0]}! 👋
                            </h2>
                            <p className="text-text-secondary mb-8 max-w-xl mx-auto">
                                Continue where you left off. Browse new resources or contribute to the community.
                            </p>
                            <div className="flex flex-wrap justify-center gap-4">
                                <Link href="/browse" className="btn btn-primary px-8 py-3">
                                    Browse Resources
                                </Link>
                                <Link href="/upload" className="btn btn-secondary px-8 py-3">
                                    Upload New
                                </Link>
                            </div>
                        </>
                    ) : (
                        <>
                            <h2 className="text-2xl md:text-3xl font-bold text-text-primary mb-4">
                                Ready to Get Started?
                            </h2>
                            <p className="text-text-secondary mb-8 max-w-xl mx-auto">
                                Join thousands of students sharing knowledge. It&apos;s free and takes less than a minute.
                            </p>
                            <div className="flex flex-wrap justify-center gap-4">
                                <Link href="/auth/register" className="btn btn-primary px-8 py-3">
                                    Create Account
                                </Link>
                                <Link href="/browse" className="btn btn-secondary px-8 py-3">
                                    Browse Resources
                                </Link>
                            </div>
                        </>
                    )}
                </div>
            </section>
        </div>
    )
}
