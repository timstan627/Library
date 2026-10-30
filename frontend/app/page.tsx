'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Search, Upload, FileText, Star } from 'lucide-react'
import { api } from '@/lib/api'
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
        api.get('/stats')
            .then(res => setStats(res.data))
            .catch(() => setStats(null))
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

    const liveStats = [
        { value: stats ? formatNumber(stats.resources) : '—', label: stats?.resources === 1 ? 'Resource' : 'Resources' },
        { value: stats ? formatNumber(stats.users) : '—', label: stats?.users === 1 ? 'Student' : 'Students' },
        { value: stats ? formatNumber(stats.downloads) : '—', label: stats?.downloads === 1 ? 'Download' : 'Downloads' },
        { value: stats ? formatNumber(stats.courses) : '—', label: stats?.courses === 1 ? 'Course' : 'Courses' },
    ]

    const features = [
        {
            icon: Upload,
            title: 'Unlimited Storage',
            body: 'Upload your notes, exams, and study materials without worrying about storage limits.',
        },
        {
            icon: Search,
            title: 'Advanced Search',
            body: 'Find what you need with filters by course, department, and tags.',
        },
        {
            icon: Star,
            title: 'Community Ratings',
            body: 'Rate and review resources so the best study materials surface to everyone.',
        },
    ]

    return (
        <div className="min-h-screen">
            {/* Hero */}
            <section className="container-custom py-16 text-center">
                <div className="max-w-3xl mx-auto">
                    <h1 className="text-4xl md:text-5xl font-bold text-text-primary mb-6 animate-fade-in">
                        Student Resource Library
                    </h1>
                    <p className="text-xl text-text-secondary mb-8 animate-slide-up">
                        Share and discover study materials, notes, and exam papers.
                    </p>

                    {/* Search */}
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

                    {/* Quick links */}
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
                                Create Account
                            </Link>
                        )}
                    </div>
                </div>
            </section>

            {/* Live stats */}
            <section className="border-y border-border-subtle bg-background-secondary py-8">
                <div className="container-custom">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
                        {liveStats.map((stat) => (
                            <div key={stat.label}>
                                <p className="text-3xl font-bold font-display text-accent-light mb-2 tabular-nums">
                                    {stat.value}
                                </p>
                                <p className="text-text-secondary">{stat.label}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Why this library */}
            <section className="container-custom py-12">
                <div className="card p-6 md:p-10">
                    <h2 className="text-2xl font-bold text-text-primary mb-8 font-display">
                        Why Use Student Library?
                    </h2>

                    <ul className="md:grid md:grid-cols-2 md:gap-x-12 md:gap-y-0 divide-y divide-border-subtle md:divide-y-0">
                        {features.map((feature, i) => (
                            <li
                                key={feature.title}
                                className={`flex items-start gap-4 py-6 md:py-8 ${i === 2 ? 'md:col-span-2 md:border-t md:border-border-subtle' : ''}`}
                            >
                                <feature.icon className="w-6 h-6 text-accent-primary shrink-0 mt-1" aria-hidden="true" />
                                <div>
                                    <h3 className="text-lg font-semibold text-text-primary mb-1.5 font-display">
                                        {feature.title}
                                    </h3>
                                    <p className="text-text-secondary">
                                        {feature.body}
                                    </p>
                                </div>
                            </li>
                        ))}
                    </ul>
                </div>
            </section>

            {/* Closing action */}
            <section className="container-custom py-12">
                <div className="card p-8 md:p-12 text-center">
                    {user ? (
                        <>
                            <h2 className="text-2xl md:text-3xl font-bold text-text-primary mb-4 font-display">
                                Welcome back, {(user.display_name || 'User').split(' ')[0]}
                            </h2>
                            <p className="text-text-secondary mb-8 max-w-xl mx-auto">
                                Continue where you left off. Browse new resources or contribute your own.
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
                            <h2 className="text-2xl md:text-3xl font-bold text-text-primary mb-4 font-display">
                                Ready to Get Started?
                            </h2>
                            <p className="text-text-secondary mb-8 max-w-xl mx-auto">
                                Join students sharing knowledge with their peers. It&apos;s free and takes less than a minute.
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
